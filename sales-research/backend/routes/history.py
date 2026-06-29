import asyncio

from db.models import Profile
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_history, get_report, get_db, _report_to_dict
from db.database import SessionLocal
from dependencies import get_current_user
import json
import logging
import time

logger = logging.getLogger(__name__)

history_router = APIRouter()

@history_router.get("/history")
async def read_history(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    status: str = "all",
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.models import ResearchReport, Profile, IdentifiedProfile
    from sqlalchemy import select, func, or_
    import os

    start_time = time.time()

    try:
        # Build shared scope predicates
        scope_filters = []
        if current_user.organization_id:
            scope_filters.append(ResearchReport.organization_id == current_user.organization_id)
        else:
            scope_filters.append(ResearchReport.created_by_id == current_user.id)

        search_filter = None
        if search:
            search_filter = or_(
                ResearchReport.fullname.ilike(f"%{search}%"),
                ResearchReport.company_name.ilike(f"%{search}%"),
                ResearchReport.website.ilike(f"%{search}%"),
                ResearchReport.linkedin_url.ilike(f"%{search}%")
            )

        rep_filter = None
        if status and status != "all":
            rep_filter = ResearchReport.created_by_id == status

        # Main list query — exclude interaction_history (large TOAST blob, only needed in detail view)
        query = (
            select(
                ResearchReport.id,
                ResearchReport.created_at,
                ResearchReport.linkedin_url,
                ResearchReport.fullname,
                ResearchReport.profile_picture_url,
                ResearchReport.website,
                ResearchReport.lead_score,
                Profile.full_name.label("rep_name"),
                IdentifiedProfile.touchpoint_count,
            )
            .outerjoin(Profile, ResearchReport.created_by_id == Profile.id)
            .outerjoin(IdentifiedProfile, ResearchReport.linkedin_url == IdentifiedProfile.linkedin_url)
            .where(*scope_filters)
        )
        if search_filter is not None:
            query = query.where(search_filter)
        if rep_filter is not None:
            query = query.where(rep_filter)

        sort_attr = None
        if sort_by == "rep_name":
            sort_attr = Profile.full_name
        elif hasattr(ResearchReport, sort_by):
            sort_attr = getattr(ResearchReport, sort_by)
        else:
            sort_attr = ResearchReport.created_at

        query = query.order_by(sort_attr.desc() if sort_order == "desc" else sort_attr.asc())
        query = query.offset(skip).limit(limit)

        # Count query — run in parallel with main query on separate session
        count_query = select(func.count()).select_from(ResearchReport).where(*scope_filters)
        if search_filter is not None:
            count_query = count_query.where(search_filter)
        if rep_filter is not None:
            count_query = count_query.where(rep_filter)

        async def _count():
            async with SessionLocal() as s:
                r = await s.execute(count_query)
                return r.scalar()

        result, total = await asyncio.gather(
            db.execute(query),
            _count(),
        )

        duration = time.time() - start_time
        logger.info("read_history: %.0fms", duration * 1000)

        history_data = []
        for row in result.all():
            history_data.append({
                "id": str(row.id),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "linkedin_url": row.linkedin_url,
                "fullname": row.fullname,
                "profile_picture_url": row.profile_picture_url,
                "website": row.website,
                "lead_score": row.lead_score,
                "rep_name": row.rep_name or "System",
                "touchpoint_count": row.touchpoint_count or 0,
            })

        return {"items": history_data, "total": total}
    except Exception as e:
        logger.error(f"Error in read_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@history_router.get("/history/{report_id}")
async def read_report_item(report_id: str, db: AsyncSession = Depends(get_db), current_user: Profile = Depends(get_current_user)):
    import time
    from db.models import IdentifiedProfile
    from sqlalchemy import select
    
    start_time = time.time()
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.organization_id != current_user.organization_id and str(report.created_by_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Unauthorized access to this report.")
    
    email_fallback = None
    verification_status = None
    if report.linkedin_url:
        stmt = select(IdentifiedProfile.email, IdentifiedProfile.email_verification_status).where(IdentifiedProfile.linkedin_url == report.linkedin_url)
        res = await db.execute(stmt)
        profile_data = res.first()
        if profile_data:
            email_fallback = profile_data[0]
            verification_status = profile_data[1]

    # Attach transiently for _report_to_dict
    setattr(report, "email_verification_status", verification_status)
    result = _report_to_dict(report, email_fallback=email_fallback)

    duration = time.time() - start_time
    logger.debug(f"read_report_item({report_id}) took {duration:.4f}s")
    return result
