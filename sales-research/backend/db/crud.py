from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from db.models import ResearchReport
from db.schemas import ResearchReportCreate

async def save_report(db: AsyncSession, report_data: ResearchReportCreate):
    db_report = ResearchReport(**report_data.dict())
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_history(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(ResearchReport).order_by(desc(ResearchReport.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_report(db: AsyncSession, report_id: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()
