from fastapi import APIRouter, Depends, Body, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional
import asyncio
import json
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_competitor_analysis, upsert_identified_profile, get_identified_profiles, batch_upsert_identified_profiles, count_identified_profiles
from db.database import SessionLocal
from utils.activity_helper import log_activity_and_notify

competitor_router = APIRouter(tags=['Competitor Analysis'], responses={404: {"description": "Not found"}},)

@competitor_router.get("/profiles")
async def get_profiles(
    skip: int = 0, 
    limit: int = 100, 
    search: str = None, 
    status: List[str] = Query(["all"]),
    sort_by: str = "touchpoint_count",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch all identified profiles with rep attribution.
    """
    from db.models import IdentifiedProfile, Profile
    from sqlalchemy import select, func, or_
    
    import time
    start_time = time.time()
    try:
        # Base query for profiles
        query = select(IdentifiedProfile, Profile.full_name).outerjoin(Profile, IdentifiedProfile.created_by_id == Profile.id)
        
        if search:
            search_filter = or_(
                IdentifiedProfile.name.ilike(f"%{search}%"),
                IdentifiedProfile.headline.ilike(f"%{search}%"),
                IdentifiedProfile.linkedin_url.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            
        if status and "all" not in status:
            if "fit" in status:
                query = query.where(IdentifiedProfile.is_fit == True)
            if "competitor" in status:
                query = query.where(IdentifiedProfile.is_competitor == True)
            if "dm" in status:
                query = query.where(IdentifiedProfile.is_decision_maker == True)
            
        # Dynamic Sorting
        sort_attr = None
        if sort_by == "rep_name":
            sort_attr = Profile.full_name
        elif hasattr(IdentifiedProfile, sort_by):
            sort_attr = getattr(IdentifiedProfile, sort_by)
        else:
            sort_attr = IdentifiedProfile.touchpoint_count

        if sort_order == "desc":
            query = query.order_by(sort_attr.desc())
        else:
            query = query.order_by(sort_attr.asc())

        query = query.offset(skip).limit(limit)
        
        db_start = time.time()
        result = await db.execute(query)
        db_end = time.time()
        print(f"DEBUG: get_profiles DB execution: {db_end - db_start:.4f}s")
        
        enriched_profiles = []
        rows = result.all()
        fetch_end = time.time()
        print(f"DEBUG: get_profiles Fetch rows: {fetch_end - db_end:.4f}s")
        
        for profile, rep_name in rows:
            p_dict = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
            # Convert UUIDs to strings for JSON
            for k, v in p_dict.items():
                if hasattr(v, 'hex'): p_dict[k] = str(v)
            p_dict["rep_name"] = rep_name or "System"
            enriched_profiles.append(p_dict)
            
        map_end = time.time()
        print(f"DEBUG: get_profiles Mapping: {map_end - fetch_end:.4f}s")
            
        # Count for pagination
        count_query = select(func.count(IdentifiedProfile.id))
        if search:
            count_query = count_query.where(search_filter)
        
        if status and "all" not in status:
            if "fit" in status:
                count_query = count_query.where(IdentifiedProfile.is_fit == True)
            if "competitor" in status:
                count_query = count_query.where(IdentifiedProfile.is_competitor == True)
            if "dm" in status:
                count_query = count_query.where(IdentifiedProfile.is_decision_maker == True)
                
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        count_end = time.time()
        print(f"DEBUG: get_profiles Count query: {count_end - map_end:.4f}s")
        print(f"DEBUG: get_profiles TOTAL: {count_end - start_time:.4f}s")
        
        return {"profiles": enriched_profiles, "total": total}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

class CompetitorInput(BaseModel):
    urls: List[str] = []

@competitor_router.post("/analyze")
async def run_competitor_analysis(input_data: CompetitorInput, db: AsyncSession = Depends(get_db)):
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
async def sse_classification(request: Request):
    """
    Server-Sent Events endpoint for classification updates.
    """
    from services.classification_service import event_manager
    queue = await event_manager.subscribe()

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
            await event_manager.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")




@competitor_router.post("/leads")
async def discover_leads(
    input_data: CompetitorInput, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
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

    try:
        all_leads = []
        raw_leads_to_save = []
        
        print(f"DEBUG: Starting parallel discovery for {len(urls)} competitors")
        
        # Parallel Execution Wrapper
        async def fetch_competitor_leads(url):
            try:
                # wrapped in to_thread because requests is blocking
                from agents.linkedin_agent import discover_leads_from_competitor
                return await asyncio.to_thread(discover_leads_from_competitor, url)
            except Exception as e:
                print(f"Error fetching leads for {url}: {e}")
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
            print(f"DEBUG: Saving {len(raw_leads_to_save)} raw leads to DB...")
            await batch_upsert_identified_profiles(db, raw_leads_to_save)
            
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
        background_tasks.add_task(run_classification_and_update, raw_leads_to_save)
        
        print(f"DEBUG: Returning {len(all_leads)} leads immediately to frontend.")
        return {"leads": all_leads}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
