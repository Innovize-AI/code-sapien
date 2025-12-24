import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import save_report, get_db, SessionLocal
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

async def run_single_research(
    linkedin_url: Optional[str] = None,
    website: Optional[str] = None,
    options: InputLeadData = None,
    email: Optional[str] = None,
    progress_callback=None  # New callback argument
):
    website = add_https_if_missing(website)
    thread_id = str(uuid.uuid4())
    thread = {"configurable": {"thread_id": thread_id}}
    
    # Fetch ICP from DB
    icp_data = None
    async with SessionLocal() as db:
        from sqlalchemy import select
        from db.models import OrganizationSettings
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        if settings and settings.icp_json:
            try:
                icp_dict = json.loads(settings.icp_json)
                # Map value_proposition to something useful if needed, or just let it be in extra fields if Pydantic allows, 
                # but IdealProfile in state.py needs to match.
                # state.py IdealProfile: industry, company_size, revenue, job_title.  
                # Our stored data has these.
                icp_data = IdealProfile(
                    industry=icp_dict.get("industry", "Technology"),
                    company_size=icp_dict.get("company_size", "10-50"),
                    revenue=icp_dict.get("revenue", "$1M+"),
                    job_title=icp_dict.get("job_title", "CTO")
                )
            except Exception as e:
                print(f"Error parsing ICP settings: {e}")

    # Fallback if no settings found (to avoid breaking existing flows immediately, though we should onboarding)
    if not icp_data:
        print("WARNING: No ICP settings found. Using defaults.")
        icp_data = IdealProfile(
            industry="Finance",
            company_size="10-50",
            revenue="$10M+",
            job_title="CTO, CEO"
        )

    ideal_profile = icp_data

    initial_state = {
        "email_id": email,
        "linkedin_url": linkedin_url,
        "website": website,
        "company_context": COMPANY_CONTEXT,
        "ideal_profile": ideal_profile,
        "input_lead_data": options
    }

    final_state = {}
    
    if options is None:
         pass 

    try:
        async for update in graph.astream(initial_state, thread, stream_mode="updates"):
            for node_name, state_update in update.items():
                final_state.update(state_update)
                
                # Send progress update if callback is provided
                if progress_callback:
                    message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                    # We pass the url to identify which lead this update is for
                    await progress_callback(linkedin_url, message)

        # Persist results to DB inside this task
        async with SessionLocal() as db:
            if final_state.get("sales_research_report"):
                report_data = ResearchReportCreate(
                    linkedin_url=linkedin_url or "",
                    website=website or "",
                    sales_research_report=final_state.get("sales_research_report"),
                    lead_score_analysis=final_state.get("lead_score_analysis"),
                    user_profile_analysis=final_state.get("user_profile_analysis"),
                    website_analysis=final_state.get("website_analysis"),
                    fullname=final_state.get("fullname"),
                    profile_picture_url=final_state.get("profile_picture_url"),
                    lead_score=None,
                    project_urgency=options.project_urgency
                )
                saved_report = await save_report(db, report_data)
                # Inject ID into final state so it's returned to frontend
                if saved_report:
                    print(f"DEBUG: Saved report with ID: {saved_report.id}")
                    final_state["id"] = str(saved_report.id)
                else:
                    print("DEBUG: Failed to save report or no object returned.")
                
        return {"linkedin_url": linkedin_url, "result": final_state}
    except Exception as e:
        # Re-raise exception so the caller knows this task failed
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
            print(f"Discovering leads using Apollo for: {input_data}")
            leads = find_leads_apollo(input_data, api_key=apollo_key)
        else:
            print(f"Discovering leads using Tavily for: {input_data}")
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
    website = add_https_if_missing(website)

    async def event_generator():
        thread_id = str(uuid.uuid4())
        thread = {"configurable": {"thread_id": thread_id}}
        
        ideal_profile = IdealProfile(
            industry="Finance",
            company_size="10-50",
            revenue="$10M+",
            job_title="CTO, CEO"
        )

        initial_state = {
            "email_id": email,
            "linkedin_url": linkedin_url,
            "website": website,
            "company_context": COMPANY_CONTEXT,
            "ideal_profile": ideal_profile,
            "input_lead_data": options
        }

        final_state = {}
        
        try:
            async for update in graph.astream(initial_state, thread, stream_mode="updates"):
                for node_name, state_update in update.items():
                    final_state.update(state_update)
                    message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                    yield f"data: {json.dumps({'status': message})}\n\n"
        except Exception as e:
            print(f"Error during graph execution: {e}")
            yield f"data: {json.dumps({'status': 'Error', 'message': str(e)})}\n\n"
            return

        # Persist results to DB
        try:
            if final_state.get("sales_research_report"):
                report_data = ResearchReportCreate(
                    linkedin_url=linkedin_url or "",
                    website=website or "",
                    sales_research_report=final_state.get("sales_research_report"),
                    lead_score_analysis=final_state.get("lead_score_analysis"),
                    user_profile_analysis=final_state.get("user_profile_analysis"),
                    website_analysis=final_state.get("website_analysis"),
                    fullname=final_state.get("fullname"),
                    profile_picture_url=final_state.get("profile_picture_url"),
                    lead_score=None,
                    project_urgency=options.project_urgency
                )
                saved_report = await save_report(db, report_data)
                if saved_report:
                    print("DEBUG: Single analysis, saved report with ID:", saved_report.id)
                    final_state["id"] = str(saved_report.id)
                print("Report saved successfully to database.")
            else:
                print("Skipping database save: No research report generated.")
        except Exception as e:
            print(f"Failed to save report: {e}")

        yield f"data: {json.dumps({'status': 'Done', 'result': final_state})}\n\n"

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
