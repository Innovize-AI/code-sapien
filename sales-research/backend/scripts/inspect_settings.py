import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path to find db
sys.path.append(os.getcwd())

from db.models import OrganizationSettings
from db.database import DATABASE_URL

async def inspect_settings():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()

        if not settings:
            print("No organization settings found.")
            return

        print(f"Total Settings Found: 1")
        print(f"ICP JSON: {settings.icp_json}")
        print(f"Selling Profile JSON: {settings.selling_profile_json}")
        
        if settings.selling_profile_json:
            try:
                profile = json.loads(settings.selling_profile_json)
                print(f"Parsed Products: {len(profile.get('products', []))}")
                for p in profile.get('products', []):
                    print(f"- {p.get('name')} (Strategic: {p.get('is_strategic_pivot')})")
            except Exception as e:
                print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_settings())
