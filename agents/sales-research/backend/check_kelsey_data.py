import asyncio
import logging

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import SessionLocal
from db.models import IdentifiedProfile, ResearchReport, Company

async def check_kelsey():
    async with SessionLocal() as db:
        # Search in IdentifiedProfile
        logger.info("Checking IdentifiedProfile for 'Kelsey'...")
        stmt = select(IdentifiedProfile).where(IdentifiedProfile.name.ilike("%Kelsey%"))
        result = await db.execute(stmt)
        profiles = result.scalars().all()
        for p in profiles:
            logger.info(f"Profile: ID={p.id}, Name={p.name}, LinkedIn={p.linkedin_url}, CompanyID={p.company_id}")
            if p.company_id:
                c_stmt = select(Company).where(Company.id == p.company_id)
                c_res = await db.execute(c_stmt)
                company = c_res.scalar_one_or_none()
                if company:
                    logger.info(f"  Associated Company: ID={company.id}, Name={company.name}, Domain={company.domain}")
                else:
                    logger.info(f"  Associated Company NOT FOUND for ID={p.company_id}")
            else:
                logger.info("  No CompanyID associated.")

        # Search in ResearchReport
        logger.info("\nChecking ResearchReport for 'Kelsey'...")
        stmt = select(ResearchReport).where(ResearchReport.fullname.ilike("%Kelsey%"))
        result = await db.execute(stmt)
        reports = result.scalars().all()
        for r in reports:
            logger.info(f"Report: ID={r.id}, Name={r.fullname}, LinkedIn={r.linkedin_url}, CompanyName={r.company_name}")

if __name__ == "__main__":
    asyncio.run(check_kelsey())
