
import asyncio
import json
from db.database import SessionLocal
from db.models import OrganizationSettings
from sqlalchemy import select

async def verify_settings_table():
    print("Verifying OrganizationSettings table...")
    async with SessionLocal() as db:
        try:
            # Try to fetch existing settings
            result = await db.execute(select(OrganizationSettings).limit(1))
            settings = result.scalars().first()
            print(f"Fetch successful. Found settings: {settings}")
            
            # Try to create/update settings
            test_data = {
                "industry": "Test Industry",
                "job_title": "Test Title"
            }
            icp_json = json.dumps(test_data)
            
            if settings:
                settings.icp_json = icp_json
                print("Updating existing settings...")
            else:
                print("Creating new settings...")
                settings = OrganizationSettings(icp_json=icp_json)
                db.add(settings)
            
            await db.commit()
            print("Commit successful!")
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(verify_settings_table())
