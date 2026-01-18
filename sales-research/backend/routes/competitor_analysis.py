from fastapi import APIRouter, Depends, Body
from typing import List
from agents.linkedin_agent import analyze_competitor_posts, discover_leads_from_competitor
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_competitor_analysis, upsert_identified_profile, get_identified_profiles, batch_upsert_identified_profiles, count_identified_profiles

competitor_router = APIRouter(tags=['Competitor Analysis'], responses={404: {"description": "Not found"}},)

@competitor_router.get("/profiles")
async def get_profiles(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Fetch all identified profiles from competitor discovery.
    """
    try:
        profiles = await get_identified_profiles(db, skip, limit)
        total = await count_identified_profiles(db)
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

@competitor_router.post("/leads")
async def get_competitor_leads(input_data: CompetitorInput, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to discover leads from competitor LinkedIn posts.
    """
    try:
        urls = input_data.urls
        if not urls:
            return {"leads": [], "message": "No competitors selected for analysis."}

        all_leads = []
        raw_leads_to_save = []
        
        print(f"DEBUG: Starting discovery for {len(urls)} competitors")
        for url in urls:
            leads = discover_leads_from_competitor(url)
            for l in leads:
                # Prepare for batch save
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "comment": l["comment_text"],
                    "source_post": l["source_post"],
                    "source_post_url": l["source_post_url"],
                    "competitor": l["competitor"]
                })
            all_leads.extend(leads)
        
        if raw_leads_to_save:
            print(f"DEBUG: Saving {len(raw_leads_to_save)} leads to DB...")
            await batch_upsert_identified_profiles(db, raw_leads_to_save)
            print("DEBUG: Batch save completed successfully")
        
        print(f"DEBUG: FINAL Returning {len(all_leads)} leads to frontend. Sample: {str(all_leads[0]) if all_leads else 'None'}")
        return {"leads": all_leads}
    except Exception as e:
        return {"error": str(e)}
