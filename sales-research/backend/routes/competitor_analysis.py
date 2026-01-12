from fastapi import APIRouter, Depends, Body
from typing import List
from agents.linkedin_agent import analyze_competitor_posts
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_competitor_analysis
import json

competitor_router = APIRouter(tags=['Competitor Analysis'], responses={404: {"description": "Not found"}},)

class CompetitorInput(BaseModel):
    urls: List[str]

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
