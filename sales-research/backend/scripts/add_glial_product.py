import asyncio
import json
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add script directory and current directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(os.getcwd())

from db.models import OrganizationSettings
from db.database import DATABASE_URL

async def add_glial_product():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Fetch current settings
        result = await session.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()

        if not settings:
            print("No organization settings found. Creating new...")
            settings = OrganizationSettings()
            session.add(settings)

        # 2. Prepare Glial Product
        glial_product = {
            "name": "Glial",
            "description": "Autonomous 'Sales Brain' infrastructure that turns raw market signals into analyst-grade execution. Bridges the 'Context Gap' using a multi-agent architecture (Intent, Scoring, Strategy) to tell teams who to contact, when, and why with hyper-personalized decision briefings.",
            "is_strategic_pivot": True,
            "target_roles": ["Founders", "VP Sales", "Marketing Directors", "RevOps Managers", "Growth Leads"],
            "relevant_files": ["market_validation/innovize-ai/glial-one-pager.md"],
            "rag_context": "market_validation/innovize-ai/glial-one-pager.md"
        }

        # 3. Update Selling Profile
        if settings.selling_profile_json:
            profile = json.loads(settings.selling_profile_json)
        else:
            profile = {
                "company_name": "Innovize AI",
                "description": "Specialized AI Transformation Provider",
                "products": []
            }

        # Check if already exists
        exists = any(p["name"] == "Glial" for p in profile.get("products", []))
        if not exists:
            # Mark others as not strategic pivot if this is the new hero
            for p in profile.get("products", []):
                p["is_strategic_pivot"] = False
            
            if "products" not in profile:
                profile["products"] = []
            profile["products"].append(glial_product)
            print(f"Added Glial to products in {profile['company_name']}")
        else:
            print("Glial already exists in products.")

        settings.selling_profile_json = json.dumps(profile)
        await session.commit()
        print("Organization settings updated successfully.")

if __name__ == "__main__":
    asyncio.run(add_glial_product())
