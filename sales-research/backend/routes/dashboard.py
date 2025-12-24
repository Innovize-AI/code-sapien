
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.database import get_db
from db.models import ResearchReport
from pydantic import BaseModel

dashboard_router = APIRouter(tags=['Dashboard'])

class DashboardStats(BaseModel):
    total_leads: int
    avg_lead_score: float
    high_potential_leads: int
    time_saved_hours: float

@dashboard_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Get aggregated statistics for the dashboard.
    """
    # Total Leads
    total_leads_query = select(func.count(ResearchReport.id))
    total_leads_result = await db.execute(total_leads_query)
    total_leads = total_leads_result.scalar() or 0

    # Average Lead Score
    avg_score_query = select(func.avg(ResearchReport.lead_score))
    avg_score_result = await db.execute(avg_score_query)
    avg_score = avg_score_result.scalar() or 0.0

    # High Potential Leads (Score > 70)
    high_potential_query = select(func.count(ResearchReport.id)).where(ResearchReport.lead_score > 70)
    high_potential_result = await db.execute(high_potential_query)
    high_potential_leads = high_potential_result.scalar() or 0

    # Estimated Time Saved (assume 30 mins per lead)
    # 30 mins = 0.5 hours
    time_saved_hours = total_leads * 0.5

    return DashboardStats(
        total_leads=total_leads,
        avg_lead_score=round(float(avg_score), 1),
        high_potential_leads=high_potential_leads,
        time_saved_hours=time_saved_hours
    )
