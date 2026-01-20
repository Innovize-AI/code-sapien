import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import save_report, get_db, SessionLocal, get_report_by_email_or_linkedin
from db.schemas import ResearchReportCreate
from utils import add_https_if_missing
from workflow.state import IdealProfile, InputLeadData
from workflow.graph import graph, NODE_STATUS_MAPPING
from prompts.sales_prompts import COMPANY_CONTEXT
from .lead_discovery import LeadDiscoveryInput, find_leads_tavily, find_leads_apollo
from pydantic import BaseModel

sales_router = APIRouter(tags=['Sales Research'], responses={404: {"description": "Not found"}},)

class LeadItem(BaseModel):
    url: Optional[str] = None
    website: Optional[str] = None

class BulkLeadInput(BaseModel):
    leads: List[LeadItem]
    options: InputLeadData

async def _get_organization_settings() -> dict:
    """Helper to fetch settings from database."""
    async with SessionLocal() as db:
        from sqlalchemy import select
        from db.models import OrganizationSettings
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        
        icp = IdealProfile(
            industry="Finance",
            company_size="10-50",
            revenue="$10M+",
            job_title="CTO, CEO"
        )
        
        user_linkedin = None
        company_linkedin = None

        if settings:
            if settings.icp_json:
                try:
                    icp = IdealProfile(**json.loads(settings.icp_json))
                except Exception as e:
                    print(f"Error parsing ICP settings: {e}")
            user_linkedin = settings.user_linkedin_url
            company_linkedin = settings.company_linkedin_url
            
        return {
            "icp": icp,
            "user_linkedin_url": user_linkedin,
            "company_linkedin_url": company_linkedin
        }


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

async def _persist_results(db, linkedin_url, website, final_state, options):
    """Common logic to save research results to DB."""
    if not final_state.get("sales_research_report"):
        print("Skipping database save: No research report generated.")
        return None

    # Extract numeric lead score if possible
    lead_score = None
    score_analysis = final_state.get("lead_score_analysis", "")
    if score_analysis:
        import re
        match = re.search(r"Score:\s*(\d+)", score_analysis)
        if match:
            try:
                lead_score = int(match.group(1))
            except:
                pass

    report_data = ResearchReportCreate(
        linkedin_url=linkedin_url or "",
        email_id=final_state.get("email_id") or "",
        website=website or "",
        sales_research_report=final_state.get("sales_research_report"),
        lead_score_analysis=score_analysis,
        user_profile_analysis=final_state.get("user_profile_analysis"),
        website_analysis=final_state.get("website_analysis"),
        fullname=final_state.get("fullname"),
        profile_picture_url=final_state.get("profile_picture_url"),
        lead_score=lead_score,
        project_urgency=options.project_urgency if options else None,
        email_history=json.dumps(final_state.get("email_history") or []),
        intent_analysis=json.dumps(final_state.get("intent_analysis") or {}),
        extra_metadata=json.dumps(final_state.get("extra_research_context") or {}),
        
        # Modular Nodules
        viability_analysis=final_state.get("viability_analysis"),
        target_pain_points=final_state.get("target_pain_points"),
        strategic_solutions=final_state.get("strategic_solutions"),
        personalized_outreach=final_state.get("personalized_outreach"),
        
        # LinkedIn Subgraph Data
        post_engagements=json.dumps(final_state.get("post_engagements") or []),
        company_news=json.dumps(final_state.get("company_news") or []),
        hiring_data=json.dumps(final_state.get("hiring_data") or [])
    )
    
    saved_report = await save_report(db, report_data)
    
    if saved_report:
        final_state["id"] = str(saved_report.id)
        return saved_report
    else:
        return None

def _report_to_dict(report):
    """Helper to convert ResearchReport model to final_state dictionary."""
    return {
        "id": str(report.id),
        "linkedin_url": report.linkedin_url,
        "email_id": report.email_id,
        "website": report.website,
        "sales_research_report": report.sales_research_report,
        "lead_score_analysis": report.lead_score_analysis,
        "user_profile_analysis": report.user_profile_analysis,
        "website_analysis": report.website_analysis,
        "fullname": report.fullname,
        "profile_picture_url": report.profile_picture_url,
        "lead_score": report.lead_score,
        "email_history": json.loads(report.email_history) if report.email_history else [],
        "intent_analysis": json.loads(report.intent_analysis) if report.intent_analysis else {},
        "extra_metadata": json.loads(report.extra_metadata) if report.extra_metadata else {},
        
        # Modular Nodules
        "viability_analysis": report.viability_analysis,
        "target_pain_points": report.target_pain_points,
        "strategic_solutions": report.strategic_solutions,
        "personalized_outreach": report.personalized_outreach,
        
        # LinkedIn Subgraph Results
        "post_engagements": json.loads(report.post_engagements) if report.post_engagements else [],
        "company_news": json.loads(report.company_news) if report.company_news else [],
        "hiring_data": json.loads(report.hiring_data) if report.hiring_data else []
    }

def _prepare_state_for_json(state):
    """Helper to convert Pydantic models in the state to dicts for JSON serialization."""
    if not state:
        return state
    
    cleaned = {}
    for k, v in state.items():
        if hasattr(v, 'dict'):
            cleaned[k] = v.dict()
        elif hasattr(v, 'model_dump'):
            cleaned[k] = v.model_dump()
        else:
            cleaned[k] = v
    return cleaned

async def _run_research_gen(linkedin_url, website, options, email):
    """Core generator that runs the research graph and yields updates."""
    website = add_https_if_missing(website)
    thread_id = str(uuid.uuid4())
    thread = {"configurable": {"thread_id": thread_id}}
    
    org_settings = await _get_organization_settings()
    ideal_profile = org_settings["icp"]

    initial_state = {
        "email_id": email,
        "linkedin_url": linkedin_url,
        "website": website,
        "company_context": COMPANY_CONTEXT,
        "ideal_profile": ideal_profile,
        "user_linkedin_url": org_settings["user_linkedin_url"],
        "company_linkedin_url": org_settings["company_linkedin_url"],
        "input_lead_data": options,

        "extra_research_context": options.extra_metadata if options else None,
        "user_profile_details": "",
        "scraped_website_content": "",
        "user_profile_analysis": "",
        "website_analysis": "",
        "lead_extracted_data": "",
        "sales_research_report": "",
        "lead_score_analysis": "",
        "viability_analysis": "",
        "target_pain_points": "",
        "strategic_solutions": "",
        "personalized_outreach": "",
        "post_engagements": [],
        "company_news": [],
        "hiring_data": []
    }

    final_state = initial_state.copy()
    
    try:
        async for update in graph.astream(initial_state, thread, stream_mode="updates"):
            for node_name, state_update in update.items():
                final_state.update(state_update)
                yield node_name, state_update, final_state
    except Exception as e:
        print(f"Error during graph execution: {e}")
        raise e

async def run_single_research(
    linkedin_url: Optional[str] = None,
    website: Optional[str] = None,
    options: InputLeadData = None,
    email: Optional[str] = None,
    progress_callback=None
):
    # Check for existing report if refresh is not requested
    if options and not options.refresh:
        async with SessionLocal() as db:
            existing = await get_report_by_email_or_linkedin(db, email_id=email, linkedin_url=linkedin_url)
            if existing:
                if progress_callback:
                    await progress_callback(linkedin_url, "Using existing report...")
                return {"linkedin_url": linkedin_url, "result": _report_to_dict(existing)}

    final_state = {}
    try:
        async for node_name, state_update, current_state in _run_research_gen(linkedin_url, website, options, email):
            final_state = current_state
            if progress_callback:
                message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                await progress_callback(linkedin_url, message)

        # Persist results to DB
        async with SessionLocal() as db:
            await _persist_results(db, linkedin_url, website, final_state, options)
                
        return {"linkedin_url": linkedin_url, "result": _prepare_state_for_json(final_state)}
    except Exception as e:
        raise e

@sales_router.post("/discover")
async def discover_leads(input_data: LeadDiscoveryInput, db: AsyncSession = Depends(get_db)):
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
        # Check for existing report if refresh is not requested
        if not options.refresh:
            existing = await get_report_by_email_or_linkedin(db, email_id=email, linkedin_url=linkedin_url)
            if existing:
                yield f"data: {json.dumps({'status': 'Using existing report...'})}\n\n"
                yield f"data: {json.dumps({'status': 'Done', 'result': _report_to_dict(existing)})}\n\n"
                return

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
