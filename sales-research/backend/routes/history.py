from db.models import Profile
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_history, get_report, get_db, _report_to_dict
from dependencies import get_current_user
import json
import logging

logger = logging.getLogger(__name__)

history_router = APIRouter()

@history_router.get("/history")
async def read_history(
    skip: int = 0, 
    limit: int = 50, 
    search: str = None,
    status: str = "all", # Filter by rep
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.models import ResearchReport, Profile, IdentifiedProfile
    from sqlalchemy import select, func, or_
    import time, os

    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    start_time = time.time()
    
    try:
        # Fetch history with joined profiles for rep attribution and interaction stats
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
                IdentifiedProfile.interaction_history
            )
            .outerjoin(Profile, ResearchReport.created_by_id == Profile.id)
            .outerjoin(IdentifiedProfile, ResearchReport.linkedin_url == IdentifiedProfile.linkedin_url)
        )
        
        if search:
            search_filter = or_(
                ResearchReport.fullname.ilike(f"%{search}%"),
                ResearchReport.company_name.ilike(f"%{search}%"),
                ResearchReport.website.ilike(f"%{search}%"),
                ResearchReport.linkedin_url.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            
        if status and status != "all":
            # Assuming status is the rep_id (UUID)
            query = query.where(ResearchReport.created_by_id == status)

        if current_user.organization_id:
            query = query.where(ResearchReport.organization_id == current_user.organization_id)
        else:
            query = query.where(ResearchReport.created_by_id == current_user.id)
        
        # Dynamic Sorting
        sort_attr = None
        if sort_by == "rep_name":
            sort_attr = Profile.full_name
        elif hasattr(ResearchReport, sort_by):
            sort_attr = getattr(ResearchReport, sort_by)
        else:
            sort_attr = ResearchReport.created_at

        if sort_order == "desc":
            query = query.order_by(sort_attr.desc())
        else:
            query = query.order_by(sort_attr.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        # Count total for pagination
        count_query = select(func.count()).select_from(ResearchReport)
        if search:
            count_query = count_query.where(search_filter)
        if status and status != "all":
            count_query = count_query.where(ResearchReport.created_by_id == status)
        if current_user.organization_id:
            count_query = count_query.where(ResearchReport.organization_id == current_user.organization_id)
        else:
            count_query = count_query.where(ResearchReport.created_by_id == current_user.id)
            
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        duration = time.time() - start_time
        logger.debug(f"read_history took {duration:.4f}s")
        
        history_data = []
        for row in result.all():
            item = {
                "id": str(row.id),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "linkedin_url": row.linkedin_url,
                "fullname": row.fullname,
                "profile_picture_url": row.profile_picture_url,
                "website": row.website,
                "lead_score": row.lead_score,
                "rep_name": row.rep_name or "System",
                "touchpoint_count": row.touchpoint_count or 0,
                "interaction_history": row.interaction_history
            }
            history_data.append(item)
            
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
