import os
import sys
import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "sales-research", "backend"))

# Mock dependencies for import
from db.database import SessionLocal
from db.models import Profile, Organization, OrganizationSettings
from dependencies import stitch_legacy_data

async def mass_migrate():
    async with SessionLocal() as db:
        print("Starting Mass Migration...")
        
        # 1. Fetch all users
        result = await db.execute(select(Profile))
        profiles = result.scalars().all()
        print(f"Found {len(profiles)} users to process.")

        is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
        PUBLIC_DOMAINS = {
            "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", 
            "protonmail.com", "proton.me", "aol.com", "zoho.com", "mail.com", "gmx.com"
        }

        for profile in profiles:
            try:
                email = profile.email.lower()
                user_id = profile.id
                email_parts = email.split("@")
                domain = email_parts[1] if len(email_parts) > 1 else None
                
                print(f"\nProcessing: {email} ({user_id})")
                
                # Check if already migrated
                user_meta = json.loads(profile.profile_metadata or "{}") if isinstance(profile.profile_metadata, str) else (profile.profile_metadata or {})
                if user_meta.get("migration_complete", False) and profile.organization_id:
                    print(f"  [Skipping] Already migrated.")
                    continue

                should_group = domain and domain not in PUBLIC_DOMAINS
                target_org = None
                
                # 1. First, try to find an organization by domain if it's a groupable domain
                if should_group:
                    org_res = await db.execute(select(Organization).where(Organization.domain == domain))
                    target_org = org_res.scalars().first()
                    if target_org:
                        print(f"  [Found] Existing organization for domain: {domain}")

                # 2. If not found by domain, try to find by the user's existing organization_id
                if not target_org and profile.organization_id:
                    org_res = await db.execute(select(Organization).where(Organization.id == profile.organization_id))
                    target_org = org_res.scalars().first()
                    if target_org:
                        print(f"  [Found] Existing organization by ID: {profile.organization_id}")

                # 3. If still not found, create a new one
                if not target_org:
                    org_name = f"{domain.split('.')[0].capitalize()} Space" if domain else f"{profile.full_name or 'User'}'s Personal Space"
                    target_org = Organization(name=org_name, domain=domain if should_group else None)
                    try:
                        db.add(target_org)
                        await db.flush() # Get ID for linking
                    except Exception:
                        await db.rollback()
                        if should_group and domain:
                            org_res = await db.execute(select(Organization).where(Organization.domain == domain))
                            target_org = org_res.scalars().first()
                        
                        if not target_org:
                            raise

                # --- PROVISIONING ---
                # 1. Link Profile
                if profile.organization_id != target_org.id:
                    profile.organization_id = target_org.id
                    if domain == "innovizeai.com" or is_trial:
                        profile.role = "admin"
                
                # 2. Settings
                settings_res = await db.execute(select(OrganizationSettings).where(OrganizationSettings.owner_id == user_id))
                settings = settings_res.scalars().first()
                
                if not settings:
                    orph_res = await db.execute(select(OrganizationSettings).where(OrganizationSettings.organization_id == None, OrganizationSettings.owner_id == None))
                    settings = orph_res.scalars().first()
                    
                    if not settings:
                        settings = OrganizationSettings(organization_id=target_org.id, owner_id=user_id)
                        db.add(settings)
                    else:
                        print(f"  [Action] Linking orphaned settings {settings.id}")
                        settings.organization_id = target_org.id
                        settings.owner_id = user_id
                else:
                    # If settings exist but org is not linked, link it
                    if settings.organization_id != target_org.id:
                        print(f"  [Action] Updating organization link for settings {settings.id}")
                        settings.organization_id = target_org.id
                
                # 3. Provision Pinecone Index
                index_name = f"tr-{target_org.id}"
                if settings.pinecone_index_name != index_name:
                    print(f"  [Action] Provisioning Pinecone index: {index_name}")
                    settings.pinecone_index_name = index_name
                    from services.knowledge_service import KnowledgeService
                    ks = KnowledgeService(index_name=index_name)
                    # We await it here in the script to be thorough
                    await ks.create_trial_index(index_name)

                # 4. Data Stitching
                print(f"  [Action] Stitching legacy data...")
                await stitch_legacy_data(db, user_id, target_org.id)
                
                # 5. Finalize
                user_meta["migration_complete"] = True
                profile.profile_metadata = json.dumps(user_meta)
                
                await db.commit()
                print(f"  [Success] Migration complete.")

            except Exception as e:
                print(f"  [Error] Failed to migrate {profile.email}: {e}")
                await db.rollback()

if __name__ == "__main__":
    asyncio.run(mass_migrate())
