import asyncio
import json
from uuid import uuid4
from sqlalchemy import select
from db.database import SessionLocal
from db.models import IdentifiedProfile, ResearchReport, Company
from services.research_service import _persist_results
from workflow.state import InputLeadData

async def verify_persistence():
    async with SessionLocal() as db:
        # 1. Create a dummy company
        company = Company(name="Test Company", domain="test.com")
        db.add(company)
        await db.flush()
        company_id = company.id
        
        # 2. Create an identified profile
        linkedin_url = "https://www.linkedin.com/in/test-user"
        profile = IdentifiedProfile(
            name="Test User",
            linkedin_url=linkedin_url,
            normalized_linkedin_url="linkedin.com/in/test-user",
            company_id=company_id
        )
        db.add(profile)
        await db.commit()
        
        # 3. Simulate state
        final_state = {
            "sales_research_report": "# Test Report",
            "company_id": company_id,
            "normalized_linkedin_url": "linkedin.com/in/test-user",
            "company_name": "Test Company",
            "fullname": "Test User"
        }
        
        options = InputLeadData()
        
        # 4. Persist results
        report = await _persist_results(db, linkedin_url, "test.com", final_state, options)
        
        if report:
            print(f"Report saved with ID: {report.id}")
            print(f"Company ID in report: {report.company_id}")
            print(f"Normalized URL in report: {report.normalized_linkedin_url}")
            
            assert report.company_id == company_id
            assert report.normalized_linkedin_url == "linkedin.com/in/test-user"
            print("SUCCESS: Persistence verified!")
        else:
            print("FAILURE: Report not saved.")

if __name__ == "__main__":
    asyncio.run(verify_persistence())
