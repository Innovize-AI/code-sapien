from typing import Any
import time
from fastapi import Depends, HTTPException, BackgroundTasks, Request
from services.auth_service import auth_service
from db.database import get_db
from db.models import Profile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, desc
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

# In-memory lock to prevent race conditions during rapid parallel API calls on first login
_PROVISIONING_LOCKS = set()

# --- Profile cache -----------------------------------------------------------
# Keyed on user_id (str). Stores (profile, cached_at) pairs.
# Evicted after _PROFILE_CACHE_TTL seconds or on explicit invalidation.
_PROFILE_CACHE: dict[str, tuple["Profile", float]] = {}
_PROFILE_CACHE_TTL = 300  # seconds — invalidated explicitly on writes, so 5min is safe


def _get_cached_profile(user_id: str):
    entry = _PROFILE_CACHE.get(user_id)
    if entry and (time.monotonic() - entry[1]) < _PROFILE_CACHE_TTL:
        return entry[0]
    return None


def _cache_profile(profile: "Profile"):
    _PROFILE_CACHE[str(profile.id)] = (profile, time.monotonic())


def _invalidate_profile_cache(user_id: str):
    _PROFILE_CACHE.pop(str(user_id), None)

async def stitch_legacy_data(db: AsyncSession, user_id: Any, org_id: Any):
    """
    Backfills organization_id for all historical records.
    Wrapper for TrialService logic to maintain backward compatibility with scripts.
    """
    from services.trial_service import trial_service
    await trial_service.stitch_legacy_data(db, user_id, org_id)

async def get_current_user(
    background_tasks: BackgroundTasks,
    token_query: str | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Extract Token (Header first, then Query)
    token = None
    if credentials:
        token = credentials.credentials
    elif token_query:
        token = token_query
        
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    import logging as _logging
    _dep_log = _logging.getLogger("dependencies")
    _dep_t0 = time.monotonic()

    user_response = auth_service.get_user(token)
    _dep_log.info("get_current_user: jwt=%.0fms", (time.monotonic() - _dep_t0) * 1000)

    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = user_response.user.id

    # --- Fast path: any returning user with an org already set ---------------
    # Covers both trial (migration_complete) and non-trial users.
    # Only skip cache if org_id is missing (new signup) or not yet linked.
    cached = _get_cached_profile(user_id)
    if cached is not None and cached.organization_id:
        _dep_log.info("get_current_user: profile cache hit in %.0fms", (time.monotonic() - _dep_t0) * 1000)
        return cached
    # -------------------------------------------------------------------------

    _dep_log.info("get_current_user: profile cache miss, running db queries")

    # Check Profile
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalars().first()
    # 1. Ensure Profile exists
    if not profile:
        # Create default user profile if missing
        try:
            # Try to get name from metadata
            user_meta = user_response.user.user_metadata or {}
            full_name = user_meta.get("full_name") or user_meta.get("name")
            
            # Fallback to email prefix
            if not full_name:
                full_name = user_response.user.email.split("@")[0].title()

            # In Trial Mode, the first user of the org should be an admin
            import os
            is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
            default_role = "admin" if is_trial else "user"

            profile = Profile(
                id=user_id, 
                email=user_response.user.email, 
                role=default_role,
                full_name=full_name
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to create user profile")

    # 2. Check and Auto-Provision Organization
    import os
    is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
    
    email = user_response.user.email.lower()
    email_parts = email.split("@")
    domain = email_parts[1] if len(email_parts) > 1 else None
    
    # Public/Generic domains that should NEVER be grouped together
    PUBLIC_DOMAINS = {
        "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", 
        "protonmail.com", "proton.me", "aol.com", "zoho.com", "mail.com", "gmx.com"
    }

    from db.models import Organization, OrganizationSettings
    should_group = domain and domain not in PUBLIC_DOMAINS
    target_org = None

    # 1. First, try to find an organization by domain if it's a groupable domain
    if should_group:
        org_res = await db.execute(select(Organization).where(Organization.domain == domain))
        target_org = org_res.scalars().first()

    # 2. Fallback to existing linkage or auto-create
    if not target_org:
        if profile.organization_id:
            org_res = await db.execute(select(Organization).where(Organization.id == profile.organization_id))
            target_org = org_res.scalars().first()
        
        if not target_org:
            from sqlalchemy.exc import IntegrityError
            try:
                async with db.begin_nested():
                    org_name = f"{domain.split('.')[0].capitalize()} Space" if domain else f"{profile.full_name or 'User'}'s Personal Space"
                    target_org = Organization(name=org_name, domain=domain if should_group else None)
                    db.add(target_org)
                    await db.flush()
            except IntegrityError:
                # Race condition: someone else inserted it. Re-fetch.
                if should_group and domain:
                    org_res = await db.execute(select(Organization).where(Organization.domain == domain))
                    target_org = org_res.scalars().first()
                
                if not target_org:
                    raise


    # 3. Ensure profile is linked synchronously for consistency
    if target_org and profile.organization_id != target_org.id:
        print(f"DEBUG: Synchronously linking profile {profile.id} to org {target_org.id}")
        profile.organization_id = target_org.id
        if domain == "innovizeai.com" or is_trial:
            profile.role = "admin"
        _invalidate_profile_cache(str(profile.id))
        await db.commit()
        
    # Failsafe: Trial users must always be admins of their space
    if is_trial and profile.role != "admin":
        profile.role = "admin"
        db.add(profile)
        _invalidate_profile_cache(str(profile.id))
        await db.commit()

    # --- BACKGROUND PROVISIONING LOGIC ---
    import json
    user_meta = json.loads(profile.profile_metadata or "{}") if isinstance(profile.profile_metadata, str) else (profile.profile_metadata or {})
    is_migrated = user_meta.get("migration_complete", False)
    is_provisioning = user_meta.get("provisioning_started", False)

    # Cache as soon as org is linked — provisioning state doesn't affect auth.
    # The 60s TTL is fine; the background task invalidates on completion anyway.
    if profile.organization_id:
        _cache_profile(profile)

    user_id_str = str(profile.id)
    if is_migrated or is_provisioning or user_id_str in _PROVISIONING_LOCKS:
        return profile
        
    # Mark as provisioning immediately to prevent parallel tasks
    _PROVISIONING_LOCKS.add(user_id_str)
    user_meta["provisioning_started"] = True
    profile.profile_metadata = json.dumps(user_meta)
    db.add(profile)
    await db.commit()

    # Define the background task with its OWN session
    async def run_provisioning_task(u_id_str, t_org_id_str):
        from db.database import SessionLocal
        from services.trial_service import trial_service
        
        async with SessionLocal() as db_session:
            try:
                print(f"DEBUG: Starting background provisioning for user {u_id_str}")
                await trial_service.onboard_trial_organization(db_session, t_org_id_str, u_id_str)
                # Bust cache so next request picks up the migrated profile
                _invalidate_profile_cache(u_id_str)
                print(f"DEBUG: Background provisioning SUCCESS for user {u_id_str}")
            except Exception as e:
                print(f"ERROR: Background provisioning failed for {u_id_str}: {e}")
            finally:
                # Always release the in-memory lock
                if u_id_str in _PROVISIONING_LOCKS:
                    _PROVISIONING_LOCKS.remove(u_id_str)

    # Spawn the background task and return immediately
    import asyncio
    asyncio.create_task(run_provisioning_task(user_id_str, str(target_org.id)))
    
    return profile

def require_admin(user: Profile = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
