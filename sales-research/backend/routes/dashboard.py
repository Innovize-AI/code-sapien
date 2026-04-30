
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, DATE, desc, or_, text, true
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta

from db.database import get_db
from db.models import ResearchReport, IdentifiedProfile, Profile
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from dependencies import get_current_user

dashboard_router = APIRouter(tags=['Dashboard'])

class UsageStats(BaseModel):
    used: int
    limit: int
    remaining: int

class DashboardStats(BaseModel):
    total_leads: int
    avg_lead_score: float
    high_potential_leads: int
    time_saved_hours: float
    trial_mode: bool = False
    research_usage: Optional[UsageStats] = None
    classification_usage: Optional[UsageStats] = None

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
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get aggregated statistics for the dashboard.
    Isolated to the current user in Trial Mode.
    """
    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"

    # Total Leads
    total_leads_query = select(func.count(ResearchReport.id))
    # Average Lead Score
    avg_score_query = select(func.avg(ResearchReport.lead_score))
    # High Potential Leads (Score > 70)
    high_potential_query = select(func.count(ResearchReport.id)).where(ResearchReport.lead_score > 70)

    if current_user.organization_id:
        total_leads_query = total_leads_query.where(ResearchReport.organization_id == current_user.organization_id)
        avg_score_query = avg_score_query.where(ResearchReport.organization_id == current_user.organization_id)
        high_potential_query = high_potential_query.where(ResearchReport.organization_id == current_user.organization_id)
    else:
        total_leads_query = total_leads_query.where(ResearchReport.created_by_id == current_user.id)
        avg_score_query = avg_score_query.where(ResearchReport.created_by_id == current_user.id)
        high_potential_query = high_potential_query.where(ResearchReport.created_by_id == current_user.id)

    total_leads_result = await db.execute(total_leads_query)
    total_leads = total_leads_result.scalar() or 0

    # Average Lead Score
    avg_score_result = await db.execute(avg_score_query)
    avg_score = avg_score_result.scalar() or 0.0

    high_potential_result = await db.execute(high_potential_query)
    high_potential_leads = high_potential_result.scalar() or 0

    # Estimated Time Saved
    time_saved_hours = total_leads * 0.5

    # Usage Calculations
    research_usage = None
    classification_usage = None

    if trial_mode:
        res_limit = int(os.getenv("TRIAL_RESEARCH_LIMIT", "5"))
        class_limit = int(os.getenv("TRIAL_CLASSIFICATION_LIMIT", "50"))

        # Classification count: Only count profiles that are actually useful (Fit OR Intent found)
        class_query = select(func.count(IdentifiedProfile.id)).where(
            or_(
                IdentifiedProfile.is_fit == True,
                IdentifiedProfile.intent.isnot(None)
            )
        )
        if current_user.organization_id:
            class_query = class_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
        else:
            class_query = class_query.where(IdentifiedProfile.created_by_id == current_user.id)

        class_res = await db.execute(class_query)
        class_used = class_res.scalar() or 0

        research_usage = UsageStats(
            used=total_leads,
            limit=res_limit,
            remaining=max(0, res_limit - total_leads)
        )
        classification_usage = UsageStats(
            used=class_used,
            limit=class_limit,
            remaining=max(0, class_limit - class_used)
        )

    return DashboardStats(
        total_leads=total_leads,
        avg_lead_score=round(float(avg_score), 1),
        high_potential_leads=high_potential_leads,
        time_saved_hours=time_saved_hours,
        trial_mode=trial_mode,
        research_usage=research_usage,
        classification_usage=classification_usage
    )

@dashboard_router.get("/dashboard/analytics", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get experimental analytics data for charts.
    Isolated to the current user in Trial Mode.
    """
    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # 1. Daily Trends
    trends_query = (
        select(cast(IdentifiedProfile.created_at, DATE).label("date"), func.count(IdentifiedProfile.id))
        .where(IdentifiedProfile.created_at >= thirty_days_ago)
        .group_by(cast(IdentifiedProfile.created_at, DATE))
        .order_by(cast(IdentifiedProfile.created_at, DATE))
    )

    # 2. Lead Quality
    hot_query = select(func.count(IdentifiedProfile.id)).where(
        IdentifiedProfile.is_fit == True,
        IdentifiedProfile.intent.in_(['interested', 'pain_point'])
    )
    qualified_query = select(func.count(IdentifiedProfile.id)).where(
        IdentifiedProfile.is_fit == True,
        or_(IdentifiedProfile.intent == None, ~IdentifiedProfile.intent.in_(['interested', 'pain_point']))
    )
    unfit_query = select(func.count(IdentifiedProfile.id)).where(IdentifiedProfile.is_fit == False)

    if current_user.organization_id:
        trends_query = trends_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
        hot_query = hot_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
        qualified_query = qualified_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
        unfit_query = unfit_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
    else:
        trends_query = trends_query.where(IdentifiedProfile.created_by_id == current_user.id)
        hot_query = hot_query.where(IdentifiedProfile.created_by_id == current_user.id)
        qualified_query = qualified_query.where(IdentifiedProfile.created_by_id == current_user.id)
        unfit_query = unfit_query.where(IdentifiedProfile.created_by_id == current_user.id)

    trends_result = await db.execute(trends_query)
    daily_trends = [AnalyticsDataPoint(date=str(r[0]), count=r[1]) for r in trends_result.all()]

    hot_res = await db.execute(hot_query)
    qual_res = await db.execute(qualified_query)
    unfit_res = await db.execute(unfit_query)

    lead_quality = {
        "Hot": hot_res.scalar() or 0,
        "Qualified": qual_res.scalar() or 0,
        "Unfit": unfit_res.scalar() or 0
    }

    # 3. Competitor & Keyword Breakdown
    posts_func = func.jsonb_array_elements(
        cast(func.coalesce(IdentifiedProfile.source_posts, '[]'), JSONB)
    ).table_valued("value").lateral("post")

    comp_select = (
        select(
            cast(posts_func.c.value, JSONB)["competitor"].astext.label("competitor_name"),
            func.count(IdentifiedProfile.id.distinct())
        )
        .join(posts_func, true())
    )

    if current_user.organization_id:
        comp_select = comp_select.where(IdentifiedProfile.organization_id == current_user.organization_id)
    else:
        comp_select = comp_select.where(IdentifiedProfile.created_by_id == current_user.id)

    comp_select = (
        comp_select.group_by(text("competitor_name"))
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
