import asyncio
import logging
import os
import sys
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path to allow importing from backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import IdentifiedProfile, OrganizationSettings
from utils.email_verifier import verify_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backtrack_email_verification():
    """
    Finds all IdentifiedProfiles with an email but no verification status,
    and runs the Million Verifier process on them.
    """
    logger.info("Starting email verification backtrack process...")
    
    async with SessionLocal() as session:
        # 1. Fetch Million Verifier API Key
        stmt = select(OrganizationSettings.million_verifier_api_key).limit(1)
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            logger.error("No Million Verifier API Key found in OrganizationSettings. Please configure it first.")
            return

        # 2. Identify profiles needing verification
        # Fetch profiles where email is present but status is missing or needs refresh
        stmt = select(IdentifiedProfile).where(
            IdentifiedProfile.email != None,
            IdentifiedProfile.email != "",
            (IdentifiedProfile.email_verification_status == None) | 
            (IdentifiedProfile.email_verification_status == "") |
            (IdentifiedProfile.email_verification_status == "not_verified")
        )
        
        result = await session.execute(stmt)
        profiles = result.scalars().all()
        
        if not profiles:
            logger.info("No profiles found needing email verification.")
            return

        logger.info(f"Found {len(profiles)} profiles to verify. Proceeding...")

        # 3. Verification Loop
        count = 0
        for profile in profiles:
            try:
                logger.info(f"Verifying {profile.email} for {profile.name or profile.linkedin_url}...")
                
                status = await verify_email(profile.email, api_key)
                
                # Update status in DB
                profile.email_verification_status = status
                session.add(profile)
                
                count += 1
                
                # Commit every 10 to be safe and show progress
                if count % 10 == 0:
                    await session.commit()
                    logger.info(f"Progress: {count}/{len(profiles)} verified.")
                
                # Small sleep to respect API limits if needed (Million Verifier is usually fast but good to be careful)
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to verify {profile.email}: {e}")
                continue
        
        await session.commit()
        logger.info(f"Finished backtracking! Total profiles verified and updated: {count}")

if __name__ == "__main__":
    asyncio.run(backtrack_email_verification())
