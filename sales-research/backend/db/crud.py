from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_
from db.models import ResearchReport
from db.schemas import ResearchReportCreate

async def save_report(db: AsyncSession, report_data: ResearchReportCreate):
    db_report = ResearchReport(**report_data.dict())
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_report_by_email_or_linkedin(db: AsyncSession, email_id: str = None, linkedin_url: str = None):
    if not email_id and not linkedin_url:
        return None
    
    conditions = []
    if email_id:
        conditions.append(ResearchReport.email_id == email_id)
    if linkedin_url:
        conditions.append(ResearchReport.linkedin_url == linkedin_url)
        
    query = select(ResearchReport).where(or_(*conditions)).order_by(desc(ResearchReport.created_at)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_history(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(ResearchReport).order_by(desc(ResearchReport.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_report(db: AsyncSession, report_id: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def save_lead_submission(db: AsyncSession, submission: ResearchReportCreate):
    from db.models import LeadSubmission
    db_item = LeadSubmission(**submission.dict())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item
