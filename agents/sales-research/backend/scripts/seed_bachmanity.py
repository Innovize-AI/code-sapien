import os
import sys
import asyncio
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "sales-research", "backend"))

from db.database import SessionLocal
from db.models import Profile, Organization, IdentifiedProfile, Company
from sqlalchemy import select

async def seed_bachmanity():
    async with SessionLocal() as db:
        print("Seeding Bachmanity Dummy Data...")
        
        # 1. Find Erlich's profile
        result = await db.execute(select(Profile).where(Profile.email == "erlich@bachmanity.com"))
        profile = result.scalars().first()
        
        if not profile:
            print("Error: Erlich's profile not found. Run seed_users.py first.")
            return

        # 2. Get or Create Organization
        org_res = await db.execute(select(Organization).where(Organization.domain == "bachmanity.com"))
        org = org_res.scalars().first()
        
        if not org:
            if profile.organization_id:
                org_res = await db.execute(select(Organization).where(Organization.id == profile.organization_id))
                org = org_res.scalars().first()
                
            if not org:
                print("Creating Bachmanity Organization...")
                org = Organization(name="Bachmanity Capital", domain="bachmanity.com")
                db.add(org)
                await db.flush()
                
                profile.organization_id = org.id
                await db.commit()

        print(f"Using Organization: {org.name} (ID: {org.id})")

        # 3. Create Dummy Companies
        companies_data = [
            {"name": "Pied Piper", "domain": "piedpiper.com", "description": "Middle-out compression startup"},
            {"name": "Aviato", "domain": "aviato.com", "description": "Aggregator of airline tickets"},
            {"name": "Hooli", "domain": "hooli.xyz", "description": "Multinational technology company"}
        ]
        
        companies = {}
        for c_data in companies_data:
            c_res = await db.execute(select(Company).where(Company.domain == c_data["domain"]))
            company = c_res.scalars().first()
            if not company:
                company = Company(**c_data)
                db.add(company)
                await db.flush()
                print(f"Created Company: {company.name}")
            companies[c_data["name"]] = company

        # 4. Create Dummy Leads (IdentifiedProfiles)
        leads_data = [
            {
                "name": "Richard Hendricks",
                "headline": "CEO at Pied Piper | Compression Enthusiast",
                "linkedin_url": "https://linkedin.com/in/rhendricks",
                "website": "piedpiper.com",
                "email": "richard@piedpiper.com",
                "is_fit": True,
                "intent": "pain_point",
                "company_id": companies["Pied Piper"].id
            },
            {
                "name": "Jian-Yang",
                "headline": "Founder at New Pied Piper | Tech Visionary",
                "linkedin_url": "https://linkedin.com/in/jianyang",
                "website": "newpiedpiper.com",
                "email": "jian@newpiedpiper.com",
                "is_fit": False,
                "intent": "curious",
                "company_id": companies["Pied Piper"].id
            },
            {
                "name": "Gavin Belson",
                "headline": "CEO at Hooli | Tech Mogul",
                "linkedin_url": "https://linkedin.com/in/gavinbelson",
                "website": "hooli.xyz",
                "email": "gavin@hooli.xyz",
                "is_fit": True,
                "intent": "interested",
                "company_id": companies["Hooli"].id
            }
        ]
        
        for l_data in leads_data:
            l_res = await db.execute(select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == l_data["linkedin_url"]))
            lead = l_res.scalars().first()
            if not lead:
                lead = IdentifiedProfile(
                    organization_id=org.id,
                    created_by_id=profile.id,
                    **l_data
                )
                db.add(lead)
                print(f"Created Lead: {lead.name}")
            
        await db.commit()
        print("Bachmanity Dummy Data Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(seed_bachmanity())
