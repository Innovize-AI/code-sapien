import asyncio
import json
from db.database import SessionLocal
from db.crud import batch_upsert_identified_profiles, get_identified_profiles
from db.models import IdentifiedProfile
from sqlalchemy import select, delete

async def verify_metadata_persistence():
    print("--- Verifying Metadata Persistence ---")
    async with SessionLocal() as session:
        async with session.begin():
            test_url = "https://www.linkedin.com/in/test-metadata-user-" + str(asyncio.get_event_loop().time())
            
            # 1. First Upsert with some metadata
            leads_1 = [
                {
                    "linkedin_url": test_url,
                    "name": "Metadata Test User",
                    "is_fit": True,
                    "profile_metadata": {"is_buy_signal": True, "is_strategic_seller": False}
                }
            ]
            print(f"Upserting first batch for {test_url}...")
            await batch_upsert_identified_profiles(session, leads_1)
        
        # 2. Verify results
        query = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == test_url)
        result = await session.execute(query)
        profile = result.scalar_one()
        
        meta = json.loads(profile.profile_metadata or "{}")
        print(f"Persisted Metadata: {meta}")
        assert meta.get("is_buy_signal") is True
        assert meta.get("is_strategic_seller") is False
        
        # 3. Second Upsert with MERGE metadata
        async with session.begin():
            leads_2 = [
                {
                    "linkedin_url": test_url,
                    "profile_metadata": {"is_fit_confirmed": True}
                }
            ]
            print(f"Upserting second batch to merge metadata...")
            await batch_upsert_identified_profiles(session, leads_2)
            
        # 4. Final Verify
        await session.refresh(profile)
        final_meta = json.loads(profile.profile_metadata or "{}")
        print(f"Final Merged Metadata: {final_meta}")
        assert final_meta.get("is_buy_signal") is True
        assert final_meta.get("is_fit_confirmed") is True
        
        print("✅ Metadata persistence and merging verified successfully!")
        
        # Cleanup
        async with session.begin():
            await session.execute(delete(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == test_url))
            print(f"Cleaned up test profile {test_url}")

if __name__ == "__main__":
    asyncio.run(verify_metadata_persistence())
