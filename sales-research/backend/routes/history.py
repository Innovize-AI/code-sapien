from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_history, get_report, get_db, _report_to_dict
import json

history_router = APIRouter()

@history_router.get("/history")
async def read_history(db: AsyncSession = Depends(get_db)):
    from db.models import ResearchReport, Profile
    from sqlalchemy import select
    
    # Fetch history with joined profiles for rep attribution
    query = (
        select(ResearchReport, Profile.full_name)
        .outerjoin(Profile, ResearchReport.created_by_id == Profile.id)
        .order_by(ResearchReport.created_at.desc())
    )
    result = await db.execute(query)
    
    history_data = []
    for report, rep_name in result.all():
        item = _report_to_dict(report)
        item["rep_name"] = rep_name or "System"
        history_data.append(item)
        
    return history_data

@history_router.get("/history/{report_id}")
async def read_report_item(report_id: str, db: AsyncSession = Depends(get_db)):
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return _report_to_dict(report)
