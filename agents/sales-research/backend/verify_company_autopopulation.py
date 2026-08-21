import asyncio
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import SessionLocal
from db.models import IdentifiedProfile, ResearchReport, Company
from services.research_service import _persist_results
from workflow.state import InputLeadData

async def verify_autopopulation():
    print("Starting verification of company autopopulation...")
    
    # 1. Setup Mock Data
    test_li_url = f"https://www.linkedin.com/in/test-kelsey-{uuid.uuid4().hex[:6]}"
    test_company_li_url = f"https://www.linkedin.com/company/test-kelsey-corp-{uuid.uuid4().hex[:6]}"
    test_domain = f"kelseycorp-{uuid.uuid4().hex[:6]}.com"
    
    final_state = {
        "sales_research_report": "This is a test report content.",
        "fullname": "Kelsey Test",
        "company_name": "Kelsey Corp",
        "company_description": "A test corporation for automation.",
        "company_industries": ["Technology", "AI"],
        "website": test_domain,
        "lead_company_linkedin_url": test_company_li_url,
        "company_stats": {
            "employee_count": 50,
            "revenue": "$10M",
            "location": "San Francisco, CA",
            "follower_count": 1000
        },
        "lead_score_analysis": {"total_score": 85},
        "ideal_profile": {},
        "extra_research_context": {}
    }
    
    options = InputLeadData()
    
    async with SessionLocal() as db:
        # Pre-create IdentifiedProfile to simulate existing lead
        print(f"Creating mock IdentifiedProfile for {test_li_url}...")
        profile = IdentifiedProfile(
            linkedin_url=test_li_url,
            name="Kelsey Test",
            normalized_linkedin_url=test_li_url
        )
        db.add(profile)
        await db.commit()
        
        # 2. Run persistence
        print("Calling _persist_results...")
        saved_report = await _persist_results(db, test_li_url, test_domain, final_state, options)
        
        if not saved_report:
            print("FAILURE: _persist_results returned None")
            return

        print(f"SUCCESS: Report saved with ID {saved_report.id}")
        
        # 3. Verify Company creation
        await db.refresh(saved_report)
        company_id = saved_report.company_id
        if not company_id:
            print("FAILURE: saved_report.company_id is None")
        else:
            print(f"SUCCESS: saved_report.company_id is {company_id}")
            
            c_stmt = select(Company).where(Company.id == company_id)
            c_res = await db.execute(c_stmt)
            company = c_res.scalar_one_or_none()
            if company:
                print(f"SUCCESS: Company found: {company.name}, {company.linkedin_url}, {company.domain}")
                if company.name == "Kelsey Corp" and company.domain == test_domain:
                    print("SUCCESS: Company data matches expectation.")
                else:
                    print(f"FAILURE: Company data mismatch. Got {company.name}, {company.domain}")
            else:
                print("FAILURE: Company NOT found in database.")
        
        # 4. Verify IdentifiedProfile link
        p_stmt = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == test_li_url)
        p_res = await db.execute(p_stmt)
        profile = p_res.scalar_one_or_none()
        if profile:
            print(f"SUCCESS: Profile found. Linked company_id: {profile.company_id}")
            if profile.company_id == company_id:
                print("SUCCESS: Profile is linked to the correct company.")
            else:
                print(f"FAILURE: Profile company_id mismatch. Got {profile.company_id}")
        else:
            print("FAILURE: Profile NOT found in database.")

if __name__ == "__main__":
    asyncio.run(verify_autopopulation())
