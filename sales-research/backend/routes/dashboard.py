
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, DATE, desc, or_, text, true
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta

from db.database import get_db
from db.models import ResearchReport, IdentifiedProfile
from pydantic import BaseModel
from typing import List, Dict

dashboard_router = APIRouter(tags=['Dashboard'])

class DashboardStats(BaseModel):
    total_leads: int
    avg_lead_score: float
    high_potential_leads: int
    time_saved_hours: float

class AnalyticsDataPoint(BaseModel):
    date: str
    count: int

class BreakdownItem(BaseModel):
    name: str
    count: int

class DashboardAnalytics(BaseModel):
    daily_trends: List[AnalyticsDataPoint]
    lead_quality: Dict[str, int]
    competitor_breakdown: List[BreakdownItem]
    keyword_breakdown: List[BreakdownItem]

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

@dashboard_router.get("/dashboard/analytics", response_model=DashboardAnalytics)
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db)):
    """
    Get experimental analytics data for charts.
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # 1. Daily Trends
    trends_query = (
        select(cast(IdentifiedProfile.created_at, DATE).label("date"), func.count(IdentifiedProfile.id))
        .where(IdentifiedProfile.created_at >= thirty_days_ago)
        .group_by(cast(IdentifiedProfile.created_at, DATE))
        .order_by(cast(IdentifiedProfile.created_at, DATE))
    )
    trends_result = await db.execute(trends_query)
    daily_trends = [AnalyticsDataPoint(date=str(r[0]), count=r[1]) for r in trends_result.all()]

    # 2. Lead Quality
    # Hot: is_fit=True AND intent in ['interested', 'pain_point']
    # Qualified: is_fit=True AND intent NOT in ['interested', 'pain_point']
    # Unfit: is_fit=False
    hot_query = select(func.count(IdentifiedProfile.id)).where(
        IdentifiedProfile.is_fit == True,
        IdentifiedProfile.intent.in_(['interested', 'pain_point'])
    )
    qualified_query = select(func.count(IdentifiedProfile.id)).where(
        IdentifiedProfile.is_fit == True,
        or_(IdentifiedProfile.intent == None, ~IdentifiedProfile.intent.in_(['interested', 'pain_point']))
    )
    unfit_query = select(func.count(IdentifiedProfile.id)).where(IdentifiedProfile.is_fit == False)

    hot_res = await db.execute(hot_query)
    qual_res = await db.execute(qualified_query)
    unfit_res = await db.execute(unfit_query)

    lead_quality = {
        "Hot": hot_res.scalar() or 0,
        "Qualified": qual_res.scalar() or 0,
        "Unfit": unfit_res.scalar() or 0
    }

    # 3. Competitor & Keyword Breakdown
    # We use jsonb_array_elements to flatten source_posts
    # source_posts is a JSON string of list of dicts: [{"competitor": "...", ...}]
    

    # Unnest source_posts JSONB array into rows, then extract the "competitor" key
    posts_func = func.jsonb_array_elements(
        cast(func.coalesce(IdentifiedProfile.source_posts, '[]'), JSONB)
    ).table_valued("value").lateral("post")

    comp_select = (
        select(
            cast(posts_func.c.value, JSONB)["competitor"].astext.label("competitor_name"),
            func.count(IdentifiedProfile.id.distinct())
        )
        .join(posts_func, true())
        .group_by(text("competitor_name"))
        .order_by(desc(func.count(IdentifiedProfile.id.distinct())))
    )

    comp_result = await db.execute(comp_select)
    
    competitor_breakdown = []
    keyword_breakdown = []
    
    for name, count in comp_result.all():
        if not name: continue
        if name.startswith("Keyword: "):
            keyword_breakdown.append(BreakdownItem(name=name.replace("Keyword: ", ""), count=count))
        else:
            competitor_breakdown.append(BreakdownItem(name=name, count=count))

    return DashboardAnalytics(
        daily_trends=daily_trends,
        lead_quality=lead_quality,
        competitor_breakdown=competitor_breakdown[:10], # Top 10
        keyword_breakdown=keyword_breakdown[:10]   # Top 10
    )
