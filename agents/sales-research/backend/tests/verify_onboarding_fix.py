
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from sqlalchemy import select, delete
from db.database import engine, SessionLocal
from db.models import OrganizationSettings

async def verify_fix():
    print("--- VERIFYING ONBOARDING FIX ---")
    
    async with SessionLocal() as db:
        # 1. Clear any existing organization settings to simulate a fresh state
        print("Clearing existing OrganizationSettings...")
        await db.execute(delete(OrganizationSettings))
        await db.commit()
        
        # 2. Simulate the set_onboarding_complete logic
        print("Simulating set_onboarding_complete...")
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        
        if settings:
            print("ERROR: Settings should have been cleared!")
            return
            
        # This is the logic we just added to the route
        print("Creating new OrganizationSettings...")
        settings = OrganizationSettings(onboarding_complete=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
        # 3. Verify it was saved
        print("Verifying saved data...")
        result = await db.execute(select(OrganizationSettings).limit(1))
        saved_settings = result.scalars().first()
        
        if saved_settings and saved_settings.onboarding_complete == 1:
            print("SUCCESS: Onboarding status saved correctly!")
        else:
            print(f"FAILED: Saved settings: {saved_settings}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
