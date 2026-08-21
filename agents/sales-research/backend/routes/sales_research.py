from services.classification_service import run_classification_and_update
import json
import os
import logging
import uuid
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import save_report, get_db, SessionLocal, get_report_by_email_or_linkedin, batch_upsert_identified_profiles, _report_to_dict, _safe_deserialize
from db.schemas import ResearchReportCreate
from utils import add_https_if_missing
from workflow.state import IdealProfile, InputLeadData
from workflow.graph import get_graph, NODE_STATUS_MAPPING
from prompts.sales_prompts import DEFAULT_COMPANY_CONTEXT
from .lead_discovery import LeadDiscoveryInput, find_leads_tavily, find_leads_apollo, enrich_and_save_leads
from utils.activity_helper import log_activity_and_notify
from pydantic import BaseModel
from dependencies import get_current_user
from db.models import Profile
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

sales_router = APIRouter(tags=['Glial Revenue Intelligence'], responses={404: {"description": "Not found"}},)

class LeadItem(BaseModel):
    url: Optional[str] = None
    website: Optional[str] = None

class BulkLeadInput(BaseModel):
    leads: List[LeadItem]
    options: InputLeadData

from services.research_service import run_single_research, _run_research_gen, _persist_results, _prepare_state_for_json, _get_organization_settings

class CheckReportsInput(BaseModel):
    leads: List[dict] # [{linkedin_url: str, email: str}]

class EnrichInput(BaseModel):
    person_ids: List[str]

@sales_router.post("/check-existing")
async def check_existing_reports(
    input_data: CheckReportsInput,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    results = {}
    if not input_data.leads:
        return results

    # Optimize with batch query
    from sqlalchemy import or_
    from db.models import ResearchReport
    
    conditions = []
    
    # Collect all emails and linkedin_urls to query in bulk
    emails = set()
    linkedin_urls = set()
    
    for lead in input_data.leads:
        l_url = lead.get("linkedin_url") or lead.get("url")
        email = lead.get("email")
        if l_url: linkedin_urls.add(l_url)
        if email: emails.add(email)
        
    # Build query
    query_conditions = []
    if linkedin_urls:
         query_conditions.append(ResearchReport.linkedin_url.in_(linkedin_urls))
    if emails:
         query_conditions.append(ResearchReport.email_id.in_(emails))
    
    if not query_conditions:
        return results
        
    stmt = select(ResearchReport).where(or_(*query_conditions))
    if current_user.organization_id:
        stmt = stmt.where(ResearchReport.organization_id == current_user.organization_id)
    else:
        stmt = stmt.where(ResearchReport.created_by_id == current_user.id)
        
    db_results = await db.execute(stmt)
    existing_reports = db_results.scalars().all()
    
    # Map results for fast lookup
    report_map = {} # Key: url or email -> Report
    for report in existing_reports:
        if report.linkedin_url:
            report_map[report.linkedin_url] = report
        if report.email_id:
            report_map[report.email_id] = report
            
    # Build response
    for lead in input_data.leads:
        linkedin_url = lead.get("linkedin_url") or lead.get("url")
        email = lead.get("email")
        
        found_report = None
        if linkedin_url and linkedin_url in report_map:
            found_report = report_map[linkedin_url]
        elif email and email in report_map:
            found_report = report_map[email]
            
        key = linkedin_url or email
        if found_report and key:
            # Fallback email from IdentifiedProfile if missing in report
            email_fallback = None
            verification_status = None
            if found_report.linkedin_url:
                from db.models import IdentifiedProfile
                stmt_prof = select(IdentifiedProfile.email, IdentifiedProfile.email_verification_status).where(IdentifiedProfile.linkedin_url == found_report.linkedin_url)
                res_prof = await db.execute(stmt_prof)
                profile_data = res_prof.first()
                if profile_data:
                    email_fallback = profile_data[0]
                    verification_status = profile_data[1]
                    
            # Attach transiently for _report_to_dict
            setattr(found_report, "email_verification_status", verification_status)

            results[key] = {
                "exists": True,
                "report_id": str(found_report.id),
                "data": _report_to_dict(found_report, email_fallback=email_fallback)
            }

    return results

@sales_router.post("/discover")
async def discover_leads(input_data: LeadDiscoveryInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: Profile = Depends(get_current_user)):
    """
    Endpoint to discover/find new leads based on criteria.
    """
    try:
        # Fetch keys from DB
        from db.crud import get_org_settings
        settings = await get_org_settings(db, org_id=current_user.organization_id, user_id=str(current_user.id))
        
        tavily_key = settings.tavily_api_key if settings else None
        apollo_key = settings.apollo_api_key if settings else None
        
        # Trial Mode Discovery Limit Check
        from utils.trial_utils import check_trial_lead_limit
        if await check_trial_lead_limit(db, org_id=current_user.organization_id, user_id=str(current_user.id)):
             return {"error": "Lead Discovery limit reached for Trial Mode. Please contact support to continue finding more leads."}
        
        if input_data.provider in ["apollo", "tavily"]:
            if os.getenv("TRIAL_MODE", "false").lower() == "true":
                provider_name = "Apollo" if input_data.provider == "apollo" else "Web Search (Tavily)"
                return {"error": f"{provider_name} is not available in Trial Mode. Please use LinkedIn Keywords or Competitor Comments."}
            leads = await find_leads_apollo(input_data, api_key=apollo_key, db=db, user_id=str(current_user.id))
            # Persist enriched Apollo leads to identified profiles
            raw_leads_to_save = []
            for lead in leads:
                url = lead.get("url", "")
                if not url:
                    continue
                meta = lead.get("metadata") or {}
                raw_leads_to_save.append({
                    "linkedin_url": url,
                    "name": lead.get("name"),
                    "headline": lead.get("comment"),
                    "comment": lead.get("comment"),
                    "source_post": "Apollo Search",
                    "source_post_url": "https://app.apollo.io/people",
                    "competitor": "Apollo",
                    "email": meta.get("email"),
                    "email_verification_status": meta.get("email_status"),
                    "website": lead.get("website"),
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": "",
                    "profile_metadata": {
                        **meta,
                        "is_enriched": lead.get("is_enriched", False),
                    },
                    "lead_source": "apollo"
                })

            if raw_leads_to_save:
                await batch_upsert_identified_profiles(
                    db, 
                    raw_leads_to_save, 
                    user_id=str(current_user.id),
                    org_id=current_user.organization_id
                )
                await db.commit()
                
                # NEW: Trigger enrichment in the background for the top 25
                # This offloads the slow waterfall process while returning results instantly.
                to_enrich_ids = [l["metadata"]["apollo_id"] for l in leads if l["metadata"].get("apollo_id")][:25]
                if to_enrich_ids:
                    from .lead_discovery import enrich_and_save_leads
                    background_tasks.add_task(
                        enrich_and_save_leads, 
                        db=db, 
                        person_ids=to_enrich_ids, 
                        user_id=str(current_user.id),
                        org_id=current_user.organization_id,
                        source_post="Apollo Discovery",
                        competitor="Apollo"
                    )
                else:
                    # Fallback to just classification if no enrichment batch identified
                    background_tasks.add_task(
                        run_classification_and_update, 
                        raw_leads_to_save, 
                        user_id=str(current_user.id),
                        org_id=current_user.organization_id
                    )
        elif input_data.provider == "linkedin_keyword":
            if not input_data.keywords:
                return {"error": "Keywords are required for this provider."}
            
            from agents.linkedin_agent import discover_leads_from_keywords
            leads_data = await discover_leads_from_keywords(input_data.keywords)
            
            # Prepare for DB and Frontend
            leads = []
            raw_leads_to_save = []
            
            for l in leads_data:
                # Map fields for consistency
                l['comment'] = l.get('comment', '')
                
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "headline": l.get("headline"),
                    "comment": l["comment"], 
                    "source_post": l.get("source_post"),
                    "source_post_url": l.get("source_post_url"),
                    "competitor": l.get("competitor"),
                    # Defaults
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": "",
                    "lead_source": "keyword"
                })

                leads.append(l)

            # Upsert and trigger background task
            if raw_leads_to_save:
                 await batch_upsert_identified_profiles(
                     db, 
                     raw_leads_to_save, 
                     user_id=str(current_user.id),
                     org_id=current_user.organization_id
                 )
                 await db.commit()
                 
                 # Log Activity: Keyword Discovery
                 import hashlib
                 kw_str = ",".join(input_data.keywords)
                 user_ref = str(current_user.id) if current_user else "system"
                 idempotency_key = f"manual_discovery:{hashlib.md5(f'{kw_str}:{user_ref}'.encode()).hexdigest()}"
                 
                 await log_activity_and_notify(
                     db,
                     type="comment",
                     title=f"Keyword Discovery: {len(raw_leads_to_save)} leads",
                     description=f"Found new leads matching keywords: {', '.join(input_data.keywords)}",
                     metadata={"keywords": input_data.keywords, "count": len(raw_leads_to_save)},
                     user_id=str(current_user.id),
                     org_id=current_user.organization_id,
                     idempotency_key=idempotency_key
                 )
                 
                 background_tasks.add_task(
                     run_classification_and_update, 
                     raw_leads_to_save, 
                     user_id=str(current_user.id),
                     org_id=current_user.organization_id
                 )
        elif input_data.provider == "linkedin_job":
            if not input_data.keywords and not input_data.job_title:
                return {"error": "Keywords or target job title are required for LinkedIn job discovery."}
                
            from agents.linkedin_agent import discover_leads_from_jobs
            # Convert keywords list to string if passed as list
            kw_param = input_data.keywords
            if isinstance(kw_param, list):
                kw_param = " ".join(kw_param)
            elif not kw_param:
                kw_param = input_data.job_title
                if isinstance(kw_param, list):
                    kw_param = " ".join(kw_param)
                    
            leads_data = await discover_leads_from_jobs(
                keywords=kw_param,
                location=input_data.location,
                sort=input_data.sort,
                date_posted=input_data.date_posted,
                easy_apply=input_data.easy_apply,
                remote=input_data.remote,
                experience=input_data.experience,
                job_type=input_data.job_type,
                company_id=input_data.company_id,
                apollo_api_key=apollo_key
            )
            
            logger.info(f"LinkedIn job leads fetched: {leads_data}")

            leads = []
            raw_leads_to_save = []
            jobs_fetched = []
            
            for l in leads_data:
                # Extract any raw jobs for the background task
                jobs_fetched.extend(l.get("profile_metadata", {}).get("hiring_jobs", []))
                
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "headline": l.get("headline"),
                    "comment": l.get("comment", ""),
                    "source_post": l.get("source_post", "LinkedIn Job Search"),
                    "source_post_url": l.get("source_post_url", ""),
                    "competitor": l.get("competitor", "LinkedIn Jobs"),
                    "website": l.get("website", ""),
                    "email": l.get("email"),
                    "email_verification_status": l.get("email_verification_status"),
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": l.get("fit_reasoning", "Locating corporate decision makers & executing AI evaluation in the background..."),
                    "lead_source": "linkedin_job",
                    "profile_metadata": l.get("profile_metadata", {})
                })
                leads.append(l)
                
            if raw_leads_to_save:
                await batch_upsert_identified_profiles(
                    db, 
                    raw_leads_to_save, 
                    user_id=str(current_user.id),
                    org_id=current_user.organization_id
                )
                await db.commit()
                
                # Log Activity: Job-based Lead Discovery
                import hashlib
                kw_str = kw_param or ""
                user_ref = str(current_user.id) if current_user else "system"
                idempotency_key = f"manual_discovery_job:{hashlib.md5(f'{kw_str}:{user_ref}'.encode()).hexdigest()}"
                
                await log_activity_and_notify(
                    db,
                    type="comment",
                    title=f"LinkedIn Job Discovery: {len(raw_leads_to_save)} leads",
                    description=f"Found new leads based on active hiring posts matching: {kw_str}",
                    metadata={"keywords": kw_str, "count": len(raw_leads_to_save)},
                    user_id=str(current_user.id),
                    org_id=current_user.organization_id,
                    idempotency_key=idempotency_key
                )
                
                from services.classification_service import enrich_linkedin_job_leads_task
                background_tasks.add_task(
                    enrich_linkedin_job_leads_task, 
                    jobs=jobs_fetched, 
                    user_id=str(current_user.id),
                    org_id=current_user.organization_id,
                    apollo_api_key=apollo_key
                )
        else:
            leads = find_leads_tavily(input_data, api_key=tavily_key)
        return {"leads": leads}
    except Exception as e:
        return {"error": str(e)}

@sales_router.post("/discover/job")
async def discover_leads_job(input_data: LeadDiscoveryInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: Profile = Depends(get_current_user)):
    """
    Endpoint to discover new leads based on LinkedIn Job searches specifically.
    """
    input_data.provider = "linkedin_job"
    return await discover_leads(input_data, background_tasks, db, current_user)

@sales_router.post("/enrich")
async def enrich_leads(input_data: EnrichInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: Profile = Depends(get_current_user)):
    """
    Endpoint to enrich Apollo leads by their person IDs.
    """
    from routes.lead_discovery import enrich_and_save_leads
    try:
        from db.crud import get_org_settings
        settings = await get_org_settings(db, org_id=current_user.organization_id, user_id=str(current_user.id))
        apollo_key = (settings.apollo_api_key if settings else None) or os.getenv("APOLLO_API_KEY")
        
        if not apollo_key:
            return {"error": "Apollo API Key is missing in Organization Settings."}

        # Use the centralized enrichment pipeline
        # This function handles waterfall, company upsert, and profile updates.
        enriched_leads = await enrich_and_save_leads(
            db=db,
            person_ids=input_data.person_ids,
            user_id=str(current_user.id),
            source_post="Manual Enrichment",
            competitor="Apollo"
        )
        
        if enriched_leads:
            # Trigger classification for the newly enriched data to update Fit/Buyer status
            from services.classification_service import run_classification_and_update
            background_tasks.add_task(run_classification_and_update, enriched_leads, user_id=str(current_user.id))
            
        return {"status": "success", "count": len(enriched_leads), "leads": enriched_leads}
    except Exception as e:
        logger.error(f"Error during enrichment route: {e}")
        return {"error": str(e)}

@sales_router.post("/")
async def run_research(
    options: InputLeadData,
    linkedin_url: Optional[str] = Query(None, description="LinkedIn profile URL"),
    website: Optional[str] = Query(None, description="Website URL"),
    email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    async def event_generator():
        # Logic moved to graph routers for intelligent skipping

        final_state = {}
        try:
            # Check for existing before streaming
            from db.crud import get_report_by_email_or_linkedin, _report_to_dict
            
            # High intent signals bypass skipping
            is_high_intent = any([
                options.refresh,
                options.trigger_context,
                options.demo_requested,
                options.download_marketing_material,
                options.referral_partner_introduction,
                options.discovery_source == 'form_fill'
            ])

            if not is_high_intent:
                existing = await get_report_by_email_or_linkedin(db, email_id=email, linkedin_url=linkedin_url)
                if existing:
                    logger.debug(f"Found existing report for {linkedin_url or email}. skipping research (low intent streaming).")
                    
                    email_fallback = None
                    if not existing.email_id and existing.linkedin_url:
                        from db.models import IdentifiedProfile
                        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == existing.linkedin_url)
                        res_prof = await db.execute(stmt_prof)
                        email_fallback = res_prof.scalar_one_or_none()
                        
                    yield f"data: {json.dumps({'status': 'Done', 'result': _report_to_dict(existing, email_fallback=email_fallback)})}\n\n"
                    return

            async for node_name, state_update, current_state in _run_research_gen(linkedin_url, website, options, email, user_id=str(current_user.id)):
                final_state = current_state
                message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                yield f"data: {json.dumps({'status': message})}\n\n"
        except Exception as e:
            error_msg = getattr(e, 'detail', str(e))
            yield f"data: {json.dumps({'status': 'Error', 'message': error_msg})}\n\n"
            return

        # Persist results to DB
        saved_report = None
        try:
            saved_report = await _persist_results(db, linkedin_url, website, final_state, options, user_id=str(current_user.id))
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

        result_payload = _prepare_state_for_json(final_state)
        if saved_report:
            result_payload["id"] = str(saved_report.id)
            try:
                from services.research_service import _push_to_hubspot_if_enabled
                await _push_to_hubspot_if_enabled(db, str(current_user.id), saved_report, final_state)
            except Exception as hs_err:
                logger.error(f"HubSpot auto-push error: {hs_err}")

        yield f"data: {json.dumps({'status': 'Done', 'result': result_payload})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@sales_router.post("/bulk")
async def run_bulk_research(
    input_data: BulkLeadInput,
    current_user: Profile = Depends(get_current_user)
):
    import asyncio
    queue = asyncio.Queue()
    
    async def progress_callback(url, status):
        # Push progress update to the queue
        await queue.put({"type": "progress", "url": url, "status": status})

    async def producer():
        tasks = []
        for lead in input_data.leads:
            tasks.append(
                run_single_research(
                    lead.url, 
                    lead.website, 
                    input_data.options, 
                    progress_callback=progress_callback,
                    user_id=str(current_user.id)
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, res in enumerate(results):
            lead_url = input_data.leads[i].url
            if isinstance(res, Exception):
                error_msg = getattr(res, 'detail', str(res))
                processed_results.append({"linkedin_url": lead_url, "error": error_msg})
            elif not res:
                processed_results.append({"linkedin_url": lead_url, "error": "Task failed silently without returning a result."})
            else:
                processed_results.append(res)
        
        # Signal done
        await queue.put({"type": "done", "results": processed_results})

    async def event_generator():
        # Start the producer task
        producer_task = asyncio.create_task(producer())
        
        yield f"data: {json.dumps({'status': 'Starting bulk analysis for ' + str(len(input_data.leads)) + ' leads'})}\n\n"

        while True:
            # Wait for data from the queue
            data = await queue.get()
            
            if data["type"] == "progress":
                # Stream the progress update
                yield f"data: {json.dumps({'status': data['status'], 'url': data['url']})}\n\n"
            
            elif data["type"] == "done":
                # Stream the final results and break loop
                yield f"data: {json.dumps({'status': 'Done', 'results': data['results']})}\n\n"
                break
            
            queue.task_done()
            
        await producer_task

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@sales_router.put("/reports/{report_id}/outreach")
async def update_outreach(
    report_id: str,
    outreach_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_outreach
    updated_report = await update_report_outreach(db, report_id, outreach_data, is_manual=True)
    if not updated_report:
        return {"error": "Report not found"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/outreach-status")
async def update_outreach_status_route(
    report_id: str,
    status_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_outreach_status
    status = status_data.get('status')
    if not status:
        return {"error": "Status is required"}
    updated_report = await update_report_outreach_status(db, report_id, status)
    if not updated_report:
        return {"error": "Report not found"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/cso-outreach")
async def update_cso_outreach(
    report_id: str,
    cso_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_cso_outreach
    updated_report = await update_report_cso_outreach(db, report_id, cso_data, is_manual=True)
    if not updated_report:
        return {"error": "Report not found or update failed"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/intent-email")
async def update_intent_email(
    report_id: str,
    email_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_intent_email
    email_text = email_data.get('email_text', '')
    updated_report = await update_report_intent_email(db, report_id, email_text)
    if not updated_report:
        return {"error": "Report not found or update failed"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/executive-blueprint")
async def update_executive_blueprint(
    report_id: str,
    blueprint_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_sales_research
    updated_report = await update_report_sales_research(db, report_id, blueprint_data, is_manual=True)
    if not updated_report:
        return {"error": "Report not found or update failed"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/intent-analysis")
async def update_intent_analysis_route(
    report_id: str,
    intent_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_intent_analysis
    updated_report = await update_report_intent_analysis(db, report_id, intent_data, is_manual=True)
    if not updated_report:
        return {"error": "Report not found or update failed"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}

@sales_router.put("/reports/{report_id}/buyer-journey")
async def update_buyer_journey_route(
    report_id: str,
    journey_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.crud import update_report_buyer_journey
    updated_report = await update_report_buyer_journey(db, report_id, journey_data, is_manual=True)
    if not updated_report:
        return {"error": "Report not found or update failed"}
        
    email_fallback = None
    if not updated_report.email_id and updated_report.linkedin_url:
        from db.models import IdentifiedProfile
        stmt_prof = select(IdentifiedProfile.email).where(IdentifiedProfile.linkedin_url == updated_report.linkedin_url)
        res_prof = await db.execute(stmt_prof)
        email_fallback = res_prof.scalar_one_or_none()
        
    return {"status": "success", "data": _report_to_dict(updated_report, email_fallback=email_fallback)}
