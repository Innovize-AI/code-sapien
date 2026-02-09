import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import save_report, get_db, SessionLocal, get_report_by_email_or_linkedin, batch_upsert_identified_profiles, _report_to_dict, _safe_deserialize
from db.schemas import ResearchReportCreate
from utils import add_https_if_missing
from workflow.state import IdealProfile, InputLeadData
from workflow.graph import graph, NODE_STATUS_MAPPING
from prompts.sales_prompts import COMPANY_CONTEXT
from .lead_discovery import LeadDiscoveryInput, find_leads_tavily, find_leads_apollo
from agents.linkedin_agent import discover_leads_from_keywords
from services.classification_service import run_classification_and_update
from utils.activity_helper import log_activity_and_notify
from pydantic import BaseModel

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

@sales_router.post("/check-existing")
async def check_existing_reports(
    input_data: CheckReportsInput,
    db: AsyncSession = Depends(get_db)
):
    results = {}
    if not input_data.leads:
        return results

    # Optimize with batch query
    from sqlalchemy import select, or_
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
             results[key] = {
                "exists": True,
                "report_id": str(found_report.id),
                "data": _report_to_dict(found_report)
            }

    return results

@sales_router.post("/discover")
async def discover_leads(input_data: LeadDiscoveryInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to discover/find new leads based on criteria.
    """
    try:
        # Fetch keys from DB
        from sqlalchemy import select
        from db.models import OrganizationSettings
        
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        
        tavily_key = settings.tavily_api_key if settings else None
        apollo_key = settings.apollo_api_key if settings else None
        
        if input_data.provider == "apollo":
            leads = find_leads_apollo(input_data, api_key=apollo_key)
        elif input_data.provider == "linkedin_keyword":
            if not input_data.keywords:
                return {"error": "Keywords are required for this provider."}
            leads_data = await discover_leads_from_keywords(input_data.keywords)
            
            # Prepare for DB and Frontend
            leads = []
            raw_leads_to_save = []
            
            for l in leads_data:
                # Map fields for consistency
                l['comment'] = l.get('comment_text', '')
                
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
                    "fit_reasoning": ""
                })
                leads.append(l)

            # Upsert and trigger background task
            if raw_leads_to_save:
                 await batch_upsert_identified_profiles(db, raw_leads_to_save)
                 
                 # Log Activity: Keyword Discovery
                 await log_activity_and_notify(
                     db,
                     type="comment",
                     title=f"Keyword Discovery: {len(raw_leads_to_save)} leads",
                     description=f"Found new leads matching keywords: {', '.join(input_data.keywords)}",
                     metadata={"keywords": input_data.keywords, "count": len(raw_leads_to_save)}
                 )
                 
                 background_tasks.add_task(run_classification_and_update, raw_leads_to_save)
        else:
            leads = find_leads_tavily(input_data, api_key=tavily_key)
        return {"leads": leads}
    except Exception as e:
        return {"error": str(e)}

@sales_router.post("/")
async def run_research(
    options: InputLeadData,
    linkedin_url: Optional[str] = Query(None, description="LinkedIn profile URL"),
    website: Optional[str] = Query(None, description="Website URL"),
    email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    async def event_generator():
        # Logic moved to graph routers for intelligent skipping

        final_state = {}
        try:
            async for node_name, state_update, current_state in _run_research_gen(linkedin_url, website, options, email):
                final_state = current_state
                message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                yield f"data: {json.dumps({'status': message})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'Error', 'message': str(e)})}\n\n"
            return

        # Persist results to DB
        try:
            await _persist_results(db, linkedin_url, website, final_state, options)
        except Exception as e:
            print(f"Failed to save report: {e}")

        yield f"data: {json.dumps({'status': 'Done', 'result': _prepare_state_for_json(final_state)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@sales_router.post("/bulk")
async def run_bulk_research(
    input_data: BulkLeadInput
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
                    progress_callback=progress_callback
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, res in enumerate(results):
            lead_url = input_data.leads[i].url
            if isinstance(res, Exception):
                processed_results.append({"linkedin_url": lead_url, "error": str(res)})
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
