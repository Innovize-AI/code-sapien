import asyncio
import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "sales-research", "backend"))

from sqlalchemy import select
from db.database import SessionLocal
from db.models import OrganizationSettings, Profile
from services.knowledge_service import KnowledgeService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_indices():
    """
    Identifies organizations missing private Pinecone indices and provisions them.
    """
    async with SessionLocal() as db:
        # 1. Find all organizations from OrganizationSettings
        result = await db.execute(select(OrganizationSettings))
        org_settings = result.scalars().all()
        
        logger.info(f"Checking {len(org_settings)} organizations...")
        
        # Pass None to avoid eager validation of non-existent index
        ks_placeholder = KnowledgeService(index_name=None)
        
        for setting in org_settings:
            org_id = setting.organization_id
            current_name = setting.pinecone_index_name
            
            # Re-provision if missing OR if using the old too-long naming convention
            if not current_name or current_name.startswith("trial-org-"):
                new_name = f"tr-{org_id}"
                logger.info(f"Organization {org_id}: Provisioning {new_name} (Old: {current_name})...")
                
                try:
                    # Provision in Pinecone (must await async method)
                    status = await ks_placeholder.create_trial_index(new_name)
                    
                    # Update DB
                    setting.pinecone_index_name = new_name
                    logger.info(f"Successfully provisioned/updated {new_name} for org {org_id}")
                except Exception as e:
                    logger.error(f"Failed to provision index for org {org_id}: {e}")
            else:
                logger.info(f"Organization {org_id} already has correct index: {current_name}")
        
        await db.commit()
        logger.info("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(backfill_indices())
