from fastapi import APIRouter, Depends, Body, BackgroundTasks, Request, Query
import time
import logging
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import defer as sa_defer
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional
import asyncio
import json
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_competitor_analysis, upsert_identified_profile, get_identified_profiles, batch_upsert_identified_profiles, count_identified_profiles
from db.database import SessionLocal
from db.models import Profile
from utils.activity_helper import log_activity_and_notify
from dependencies import get_current_user

# Large TOAST columns not needed for the list view — deferring them removes them
# from the SQL SELECT entirely, which is the primary cause of Disk IO exhaustion.
_PROFILE_LIST_DEFER = {"source_posts", "comment_history"}

logger = logging.getLogger(__name__)

competitor_router = APIRouter(tags=['Competitor Analysis'], responses={404: {"description": "Not found"}},)

@competitor_router.get("/profiles")
async def get_profiles(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    status: List[str] = Query(["all"]),
    source: str = "all",
    date_start: str = None,
    date_end: str = None,
    sort_by: str = "touchpoint_count",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Fetch identified profiles with rep attribution, source filtering, and pagination.
    """
    from db.models import IdentifiedProfile, Profile, ResearchReport, Company
    from sqlalchemy import text as sa_text
    from db.database import SessionLocal as async_session_factory
    start_time = time.time()
    try:
        # --- Shared filter builder ---
        def build_where_clauses(src, search_filter=None):
            clauses = []
            if src == "apollo":
                clauses.append(IdentifiedProfile.lead_source == "apollo")
            elif src == "keyword":
                clauses.append(IdentifiedProfile.lead_source == "keyword")
            elif src == "competitor":
                clauses.append(IdentifiedProfile.lead_source == "competitor")
            elif src == "job":
                clauses.append(IdentifiedProfile.lead_source.in_(["linkedin_job", "job"]))
            if search_filter is not None:
                clauses.append(search_filter)
            if status and "all" not in status:
                if "fit" in status:
                    clauses.append(IdentifiedProfile.is_fit == True)
                if "competitor" in status:
                    clauses.append(IdentifiedProfile.is_competitor == True)
                if "dm" in status:
                    clauses.append(IdentifiedProfile.is_decision_maker == True)
            if date_start:
                from datetime import datetime
                clauses.append(IdentifiedProfile.created_at >= datetime.fromisoformat(date_start.replace("Z", "+00:00")))
            if date_end:
                from datetime import datetime
                clauses.append(IdentifiedProfile.created_at <= datetime.fromisoformat(date_end.replace("Z", "+00:00")))
            if current_user.organization_id:
                clauses.append(IdentifiedProfile.organization_id == current_user.organization_id)
            else:
                clauses.append(IdentifiedProfile.created_by_id == current_user.id)
                
            return clauses

        search_filter = None
        if search:
            search_filter = or_(
                IdentifiedProfile.name.ilike(f"%{search}%"),
                IdentifiedProfile.headline.ilike(f"%{search}%"),
                IdentifiedProfile.linkedin_url.ilike(f"%{search}%"),
            )

        where_clauses = build_where_clauses(source, search_filter)

        # --- LATERAL join for latest report (uses index, avoids full DISTINCT ON scan) ---
        lateral_sub = (
            select(ResearchReport.id.label("report_id"))
            .where(ResearchReport.normalized_linkedin_url == IdentifiedProfile.normalized_linkedin_url)
            .order_by(ResearchReport.created_at.desc())
            .limit(1)
            .correlate(IdentifiedProfile)
            .lateral("latest_report")
        )

        # --- Sorting ---
        if sort_by == "rep_name":
            sort_attr = Profile.full_name
        elif hasattr(IdentifiedProfile, sort_by):
            sort_attr = getattr(IdentifiedProfile, sort_by)
        else:
            sort_attr = IdentifiedProfile.touchpoint_count
        order_expr = sort_attr.desc() if sort_order == "desc" else sort_attr.asc()

        # --- Main data query ---
        # Defer TOAST blobs — they are excluded from the SQL SELECT, cutting Disk IO
        # dramatically on large result sets. The detail view loads them via /profiles/{id}.
        _defer_opts = [
            sa_defer(getattr(IdentifiedProfile, col))
            for col in _PROFILE_LIST_DEFER
        ]
        data_query = (
            select(IdentifiedProfile, Profile.full_name, lateral_sub.c.report_id, Company)
            .options(*_defer_opts)
            .outerjoin(Profile, IdentifiedProfile.created_by_id == Profile.id)
            .outerjoin(Company, IdentifiedProfile.company_id == Company.id)
            .outerjoin(lateral_sub, sa_text("true"))
            .where(*where_clauses)
            .order_by(order_expr)
            .offset(skip)
            .limit(limit)
        )

        # --- Combined counts query (1 query for total + all 5 tab badges) ---
        count_base_clauses = build_where_clauses("all", search_filter)
        counts_query = select(
            func.count().label("total_all"),
            func.count().filter(IdentifiedProfile.lead_source == "apollo").label("apollo"),
            func.count().filter(IdentifiedProfile.lead_source == "keyword").label("keyword"),
            func.count().filter(IdentifiedProfile.lead_source == "competitor").label("competitor"),
            func.count().filter(IdentifiedProfile.lead_source.in_(["linkedin_job", "job"])).label("job"),
            # Total for current source tab (for pagination)
            func.count().filter(
                *(
                    [IdentifiedProfile.lead_source.in_(["linkedin_job", "job"])] if source == "job" else
                    ([IdentifiedProfile.lead_source == source] if source != "all" else [sa_text("true")])
                )
            ).label("current_total"),
        ).where(*count_base_clauses)

        db_start = time.time()
        # Run data query and counts query concurrently via two sessions
        async with async_session_factory() as db2:
            data_result, counts_result = await asyncio.gather(
                db.execute(data_query),
                db2.execute(counts_query),
            )
        db_end = time.time()
        logger.debug(f"get_profiles parallel queries: {db_end - db_start:.4f}s")

        counts_row = counts_result.one()
        tab_counts = {
            "all": counts_row.total_all,
            "apollo": counts_row.apollo,
            "keyword": counts_row.keyword,
            "competitor": counts_row.competitor,
            "job": counts_row.job,
        }
        total = counts_row.current_total

        # --- Map rows to response dicts ---
        enriched_profiles = []
        for profile, rep_name, report_id, company in data_result.all():
            try:
                p_dict = json.loads(profile.profile_metadata or "{}") if isinstance(profile.profile_metadata, str) else (profile.profile_metadata or {})
                if not isinstance(p_dict, dict): p_dict = {}
            except Exception:
                p_dict = {}

            columns_dict = {
                c.name: getattr(profile, c.name)
                for c in profile.__table__.columns
                if c.name not in _PROFILE_LIST_DEFER
            }
            for k, v in columns_dict.items():
                if v is not None or k not in p_dict:
                    p_dict[k] = v

            for k, v in list(p_dict.items()):
                if hasattr(v, 'hex'): p_dict[k] = str(v)

            p_dict["rep_name"] = rep_name or "System"
            p_dict["latest_report_id"] = str(report_id) if report_id else None

            if company:
                p_dict["company"] = {c.name: getattr(company, c.name) for c in company.__table__.columns}
                for ck, cv in p_dict["company"].items():
                    if hasattr(cv, 'hex'): p_dict["company"][ck] = str(cv)
            else:
                p_dict["company"] = None

            enriched_profiles.append(p_dict)

        logger.debug(f"get_profiles TOTAL: {time.time() - start_time:.4f}s")
        return {"profiles": enriched_profiles, "total": total, "tab_counts": tab_counts}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"error": str(e)}

@competitor_router.post("/profiles/{profile_id}/discover-audience")
async def trigger_audience_discovery(
    profile_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Manually triggers audience discovery (fetching commenters) for a specific profile.
    Useful for 'Strategic Sellers' spotted in the UI, avoiding automated infinite loops.
    """
    try:
        from db.models import IdentifiedProfile
        result = await db.execute(select(IdentifiedProfile).where(IdentifiedProfile.id == profile_id))
        profile = result.scalar_one_or_none()
        
        if not profile or not profile.linkedin_url:
            return {"error": "Profile or LinkedIn URL not found"}
            
        from services.task_service import strategic_seller_discovery_task
        # Dispatch to background
        background_tasks.add_task(
            strategic_seller_discovery_task, 
            seller_url=profile.linkedin_url, 
            user_id=str(current_user.id),
            org_id=current_user.organization_id
        )
        
        return {
            "status": "success", 
            "message": f"Started background discovery for {profile.name}'s audience."
        }
    except Exception as e:
        logger.error(f"Error triggering audience discovery: {e}", exc_info=True)
        return {"error": str(e)}

class CompetitorInput(BaseModel):
    urls: List[str] = []

@competitor_router.post("/analyze")
async def run_competitor_analysis(
    input_data: CompetitorInput, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Endpoint to analyze competitor LinkedIn posts.
    """
    try:
        from agents.linkedin_agent import analyze_competitor_posts
        report = analyze_competitor_posts(input_data.urls)
        
        # Save to DB
        await save_competitor_analysis(db, ",".join(input_data.urls), report)
        
        return {"report": report}
    except Exception as e:
        return {"error": str(e)}



@competitor_router.get("/events/classification")
async def sse_classification(
    request: Request,
    current_user: Profile = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint for classification updates.
    """
    from services.classification_service import event_manager
    org_id = current_user.organization_id
    queue = await event_manager.subscribe(org_id)

    async def event_generator():
        try:
            # Send initial ping to confirm connection
            yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                # Wait for data
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            from services.classification_service import event_manager
            await event_manager.unsubscribe(org_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")




@competitor_router.post("/leads")
async def discover_leads(
    input_data: CompetitorInput, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Discover leads from competitor posts.
    Full extraction with immediate return + Background AI Classification.
    Uses concurrency to process multiple competitors in parallel.
    """
    import asyncio
    
    urls = input_data.urls
    if not urls:
        return {"error": "No URLs provided"}

    # Trial Mode Discovery Limit Check
    from utils.trial_utils import check_trial_lead_limit
    if await check_trial_lead_limit(db, org_id=current_user.organization_id, user_id=str(current_user.id)):
         return {"error": "Lead Discovery limit reached for Trial Mode. Please upgrade to continue finding more leads."}

    try:
        all_leads = []
        raw_leads_to_save = []
        
        logger.debug(f"Starting parallel discovery for {len(urls)} competitors")
        
        # Parallel Execution Wrapper
        async def fetch_competitor_leads(url):
            try:
                # wrapped in to_thread because requests is blocking
                from agents.linkedin_agent import discover_leads_from_competitor
                return await asyncio.to_thread(discover_leads_from_competitor, url)
            except Exception as e:
                logger.error(f"Error fetching leads for {url}: {e}")
                return []

        # Launch all tasks
        tasks = [fetch_competitor_leads(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for leads in results:
            for l in leads:
                # Prepare for batch save (Raw first)
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "headline": l.get("headline"),
                    "comment": l["comment"],
                    "source_post": l["source_post"],
                    "source_post_url": l["source_post_url"],
                    "competitor": l["competitor"],
                    "is_fit": False, # Default
                    "is_competitor": False, # Default
                    "is_decision_maker": False, # Default
                    "fit_reasoning": "" # Default
                })
            all_leads.extend(leads)
        
        # 1. Save Raw Leads Immediately
        if raw_leads_to_save:
            logger.debug(f"Saving {len(raw_leads_to_save)} raw leads to DB...")
            # Assign attribution before save
            for l in raw_leads_to_save:
                l["created_by_id"] = current_user.id
                l["organization_id"] = current_user.organization_id

            await batch_upsert_identified_profiles(db, raw_leads_to_save)
            await db.commit()
            
            # Log Activity (One summary activity for the batch)
            import hashlib
            url_hash = hashlib.md5(",".join(urls).encode()).hexdigest()
            idempotency_key = f"competitor_discovery:{url_hash}"

            await log_activity_and_notify(
                db,
                type="comment",
                title=f"Discovered {len(raw_leads_to_save)} potential leads",
                description=f"Identified new commenters on competitor posts ({', '.join(urls[:2])}...)",
                metadata={"urls": urls, "count": len(raw_leads_to_save)},
                idempotency_key=idempotency_key
            )
            
        # 2. Trigger Background Classification
        from services.classification_service import run_classification_and_update
        background_tasks.add_task(
            run_classification_and_update, 
            raw_leads_to_save, 
            user_id=str(current_user.id),
            org_id=current_user.organization_id
        )
        
        logger.debug(f"Returning {len(all_leads)} leads immediately to frontend.")
        return {"leads": all_leads}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"error": str(e)}
