from fastapi import APIRouter, Depends, Body, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict
import asyncio
import json
from agents.linkedin_agent import analyze_competitor_posts, discover_leads_from_competitor, batch_classify_profiles, batch_classify_profiles_async
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_competitor_analysis, upsert_identified_profile, get_identified_profiles, batch_upsert_identified_profiles, count_identified_profiles
from db.database import SessionLocal
from services.classification_service import event_manager, run_classification_and_update
from utils.activity_helper import log_activity_and_notify

competitor_router = APIRouter(tags=['Competitor Analysis'], responses={404: {"description": "Not found"}},)

@competitor_router.get("/profiles")
async def get_profiles(
    skip: int = 0, 
    limit: int = 100, 
    search: str = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch all identified profiles from competitor discovery.
    """
    try:
        profiles = await get_identified_profiles(db, skip, limit, search_query=search)
        total = await count_identified_profiles(db, search_query=search)
        return {"profiles": profiles, "total": total}
    except Exception as e:
        return {"error": str(e)}

class CompetitorInput(BaseModel):
    urls: List[str] = []

@competitor_router.post("/analyze")
async def run_competitor_analysis(input_data: CompetitorInput, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to analyze competitor LinkedIn posts.
    """
    try:
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
                    "comment": l["comment_text"],
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
            await log_activity_and_notify(
                db,
                type="comment",
                title=f"Discovered {len(raw_leads_to_save)} potential leads",
                description=f"Identified new commenters on competitor posts ({', '.join(urls[:2])}...)",
                metadata={"urls": urls, "count": len(raw_leads_to_save)}
            )
            
        # 2. Trigger Background Classification
        background_tasks.add_task(run_classification_and_update, raw_leads_to_save)
        
        print(f"DEBUG: Returning {len(all_leads)} leads immediately to frontend.")
        return {"leads": all_leads}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
