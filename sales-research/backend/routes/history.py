from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_history, get_report, get_db
import json

history_router = APIRouter()

@history_router.get("/history")
async def read_history(db: AsyncSession = Depends(get_db)):
    data = await get_history(db)
    return data

@history_router.get("/history/{report_id}")
async def read_report_item(report_id: str, db: AsyncSession = Depends(get_db)):
    data = await get_report(db, report_id)
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Convert SQLAlchemy model to dict
    result = {
        "id": str(data.id),
        "created_at": data.created_at.isoformat() if data.created_at else None,
        "linkedin_url": data.linkedin_url,
        "email_id": data.email_id,
        "website": data.website,
        "fullname": data.fullname,
        "profile_picture_url": data.profile_picture_url,
        "sales_research_report": data.sales_research_report,
        "lead_score_analysis": data.lead_score_analysis,
        "user_profile_analysis": data.user_profile_analysis,
        "website_analysis": data.website_analysis,
        "lead_score": data.lead_score,
        "project_urgency": data.project_urgency,
    }
    
    # Parse JSON strings to objects
    if data.email_history:
        try:
            result["email_history"] = json.loads(data.email_history)
        except:
            result["email_history"] = []
    
    if data.intent_analysis:
        try:
            result["intent_analysis"] = json.loads(data.intent_analysis)
        except:
            result["intent_analysis"] = {}
    
    return result
