
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

from db.database import get_db
from db.models import OrganizationSettings, Profile, ResearchReport, IdentifiedProfile
from db.schemas import OrganizationSettingsCreate, OrganizationSettings as OrganizationSettingsSchema, IdealProfileData, IntegrationSettings, SellingProfileConfig
from dependencies import get_current_user, require_admin
import os
from services.knowledge_service import KnowledgeService
from sqlalchemy import func, or_, desc
from db.crud import get_org_settings
from utils.trial_utils import get_trial_limits

settings_router = APIRouter(tags=['Settings'])

@settings_router.get("/settings/personal-icp", response_model=Optional[IdealProfileData])
async def get_personal_icp(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get the ICP. Returns user-specific ICP if exists, otherwise global.
    """
    from db.crud import get_user_settings
    user_settings = await get_user_settings(db, str(current_user.id))
    
    if user_settings and user_settings.icp_json:
        try:
            return IdealProfileData(**json.loads(user_settings.icp_json))
        except:
            pass

    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    if not settings or not settings.icp_json:
        return None
        
    try:
        data = json.loads(settings.icp_json)
        return IdealProfileData(**data)
    except:
        return None

@settings_router.get("/settings/global-icp", response_model=Optional[IdealProfileData])
async def get_global_icp(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get the Global Organization ICP.
    """
    print("current user org id", current_user.organization_id)
    print("current user id", current_user.id)
    
    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    if not settings or not settings.icp_json:
        return None
        
    try:
        data = json.loads(settings.icp_json)
        return IdealProfileData(**data)
    except:
        return None

@settings_router.post("/settings/personal-icp", response_model=IdealProfileData)
async def save_personal_icp(
    icp_data: IdealProfileData, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Save Personal ICP Override for the current user. 
    If the settings match the Global ICP, we clear the personal override 
    to prevent redundant data and enable automatic fallback.
    If the settings are completely empty, we skip the update to avoid accidental clearing.
    """
    from db.crud import upsert_user_settings, delete_user_icp_override

    # 0. Check if data is truly empty across all fields
    def is_val_empty(v):
        if v is None: return True
        if isinstance(v, list): return len(v) == 0
        if isinstance(v, str): return not v.strip()
        return False

    is_empty = all([
        is_val_empty(icp_data.industry),
        is_val_empty(icp_data.company_size),
        is_val_empty(icp_data.revenue),
        is_val_empty(icp_data.job_title),
        is_val_empty(icp_data.value_proposition)
    ])
    
    if is_empty:
        logger.info(f"Skipping update for completely empty ICP data for user {current_user.id}")
        return icp_data
    
    # 1. Fetch ICP to compare (User-aware)
    global_settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    is_redundant = False
    if global_settings and global_settings.icp_json:
        try:
            global_icp_data = json.loads(global_settings.icp_json)
            # Compare the incoming data with global (ignoring small formatting diffs via dict compare)
            if icp_data.dict() == global_icp_data:
                is_redundant = True
        except:
            pass

    if is_redundant:
        logger.info(f"Clearing redundant ICP override for user {current_user.id}")
        await delete_user_icp_override(db, str(current_user.id))
    else:
        await upsert_user_settings(db, str(current_user.id), {"icp_json": icp_data.json()})
    
    return icp_data

@settings_router.post("/settings/global-icp", response_model=IdealProfileData)
async def save_global_icp(
    icp_data: IdealProfileData, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Save Global Organization ICP. Admin only.
    """
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    icp_json_str = icp_data.json()
    
    if settings and (settings.organization_id == admin_user.organization_id or settings.owner_id == admin_user.id):
        settings.icp_json = icp_json_str
    else:
        settings = OrganizationSettings(icp_json=icp_json_str, owner_id=admin_user.id, organization_id=admin_user.organization_id)
        db.add(settings)
    
    await db.commit()
    return icp_data

@settings_router.get("/settings/user-integrations")
async def get_user_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get personal integration settings for the current user.
    """
    from db.crud import get_user_settings
    settings = await get_user_settings(db, str(current_user.id))
    
    if not settings:
        return {
            "user_linkedin_url": None,
            "email_config": None
        }
        
    return {
        "user_linkedin_url": settings.user_linkedin_url,
        "email_config": settings.email_config,
        "slack_user_id": settings.slack_user_id
    }

@settings_router.post("/settings/user-integrations")
async def save_user_integrations(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Save personal integration settings.
    """
    from db.crud import upsert_user_settings
    await upsert_user_settings(db, str(current_user.id), data)
    return {"status": "success"}

@settings_router.get("/settings/integrations", response_model=IntegrationSettings)
async def get_integrations(
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    
    if not settings:
        return IntegrationSettings()
    
    # Parse integrations_config JSON
    int_config = {}
    if settings.integrations_config:
        try:
            int_config = json.loads(settings.integrations_config)
        except:
            int_config = {}

    # Parse million_verifier from config safely (handle both bool and {"enabled": bool})
    mv_config = int_config.get("million_verifier", False)
    if isinstance(mv_config, dict):
        mv_enabled = mv_config.get("enabled", False)
    else:
        mv_enabled = bool(mv_config)
    return IntegrationSettings(
        tavily_api_key=settings.tavily_api_key,
        apollo_api_key=settings.apollo_api_key,
        email_config=settings.email_config,
        integrations_config=settings.integrations_config,
        kit_api_key=settings.kit_api_key,
        kit_api_secret=settings.kit_api_secret,
        user_linkedin_url=settings.user_linkedin_url,
        company_linkedin_url=settings.company_linkedin_url,
        slack_webhook_url=settings.slack_webhook_url,
        discovery_keywords=settings.discovery_keywords,
        apollo_search_config=settings.apollo_search_config,
        hubspot_access_token=settings.hubspot_access_token,
        hubspot_sync_enabled=settings.hubspot_sync_enabled,
        million_verifier_api_key=settings.million_verifier_api_key,
        million_verifier_enabled=mv_enabled,
    )


@settings_router.post("/settings/integrations", response_model=IntegrationSettings)
async def save_integrations(
    data: IntegrationSettings, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    
    if trial_mode:
        # Strictly block premium integrations
        data.hubspot_access_token = None
        data.hubspot_sync_enabled = False
        data.tavily_api_key = None
        data.apollo_api_key = None
        data.kit_api_key = None
        data.kit_api_secret = None
        data.million_verifier_api_key = None
        data.million_verifier_enabled = False
        
        # Only allow Slack in integrations_config
        try:
            config = json.loads(data.integrations_config or "{}")
            new_config = {"slack": config.get("slack", {"enabled": False})}
            data.integrations_config = json.dumps(new_config)
        except:
            data.integrations_config = json.dumps({"slack": {"enabled": False}})

    if settings and (settings.organization_id == admin_user.organization_id or settings.owner_id == admin_user.id):
        settings.tavily_api_key = data.tavily_api_key
        settings.apollo_api_key = data.apollo_api_key
        settings.user_linkedin_url = data.user_linkedin_url
        settings.company_linkedin_url = data.company_linkedin_url
        settings.email_config = data.email_config
        settings.integrations_config = data.integrations_config
        settings.kit_api_key = data.kit_api_key
        settings.kit_api_secret = data.kit_api_secret
        settings.slack_webhook_url = data.slack_webhook_url
        settings.discovery_keywords = data.discovery_keywords
        settings.apollo_search_config = data.apollo_search_config
        settings.hubspot_access_token = data.hubspot_access_token
        settings.hubspot_sync_enabled = data.hubspot_sync_enabled
        settings.million_verifier_api_key = data.million_verifier_api_key
        
        # Update JSON config for million_verifier
        try:
            int_config = json.loads(settings.integrations_config or "{}")
        except:
            int_config = {}
        
        # Pop legacy key if it exists
        int_config.pop("million_verifier_enabled", None)
        # Store as dictionary for backward compatibility with nested frontend logic
        int_config["million_verifier"] = {"enabled": data.million_verifier_enabled}
        settings.integrations_config = json.dumps(int_config)
    else:
        settings = OrganizationSettings(
            owner_id=admin_user.id,
            organization_id=admin_user.organization_id,
            tavily_api_key=data.tavily_api_key, 
            apollo_api_key=data.apollo_api_key,
            email_config=data.email_config,
            integrations_config=json.dumps({
                "million_verifier": {"enabled": data.million_verifier_enabled},
            }),
            kit_api_key=data.kit_api_key,
            kit_api_secret=data.kit_api_secret,
            user_linkedin_url=data.user_linkedin_url,
            company_linkedin_url=data.company_linkedin_url,
            slack_webhook_url=data.slack_webhook_url,
            discovery_keywords=data.discovery_keywords,
            apollo_search_config=data.apollo_search_config,
            hubspot_access_token=data.hubspot_access_token,
            hubspot_sync_enabled=data.hubspot_sync_enabled,
            million_verifier_api_key=data.million_verifier_api_key,
        )

        db.add(settings)
        
    await db.commit()
    await db.refresh(settings)
    return data

@settings_router.get("/settings/onboarding-status")
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    # Check migration status from profile metadata
    import json
    user_meta = json.loads(current_user.profile_metadata or "{}") if isinstance(current_user.profile_metadata, str) else (current_user.profile_metadata or {})
    is_migrated = user_meta.get("migration_complete", False)
    
    return {
        "complete": bool(settings.onboarding_complete) if settings else False,
        "migration_complete": is_migrated
    }

@settings_router.post("/settings/onboarding-complete")
async def set_onboarding_complete(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    if settings and (settings.organization_id == current_user.organization_id or settings.owner_id == current_user.id):
        settings.onboarding_complete = 1
    else:
        # Create user settings if they don't exist
        settings = OrganizationSettings(
            onboarding_complete=1, 
            owner_id=current_user.id,
            organization_id=current_user.organization_id
        )
        db.add(settings)
    await db.commit()
    return {"status": "success"}

@settings_router.post("/settings/onboarding-reset")
async def reset_onboarding(
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Dev/admin utility: reset onboarding_complete to 0 so the onboarding flow
    is shown again. Use this instead of manually editing Supabase.
    The correct column is `onboarding_complete` in `organization_settings` — NOT `onboarding_step`.
    """
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    if settings:
        settings.onboarding_complete = 0
        await db.commit()
    return {"status": "reset", "onboarding_complete": 0}

@settings_router.get("/settings/usage")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get the current usage statistics for the user (Research & Classification).
    Useful for displaying trial limits.
    """
    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    limits = get_trial_limits()
    research_limit = limits["research_limit"]
    classification_limit = limits["classification_limit"]
    identified_limit = limits["identified_limit"]

    # Count Researches
    res_count_query = select(func.count(ResearchReport.id))
    if current_user.organization_id:
        res_count_query = res_count_query.where(ResearchReport.organization_id == current_user.organization_id)
    else:
        res_count_query = res_count_query.where(ResearchReport.created_by_id == current_user.id)
        
    res_result = await db.execute(res_count_query)
    research_used = res_result.scalar() or 0

    # Count Classifications: Only count profiles that are actually useful (Fit OR Intent found)
    class_count_query = select(func.count(IdentifiedProfile.id)).where(
        or_(
            IdentifiedProfile.is_fit == True,
            IdentifiedProfile.intent.isnot(None)
        )
    )
    if current_user.organization_id:
        class_count_query = class_count_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
    else:
        class_count_query = class_count_query.where(IdentifiedProfile.created_by_id == current_user.id)
        
    class_result = await db.execute(class_count_query)
    classification_used = class_result.scalar() or 0

    # Count Identified Profiles (Total)
    id_count_query = select(func.count(IdentifiedProfile.id))
    if current_user.organization_id:
        id_count_query = id_count_query.where(IdentifiedProfile.organization_id == current_user.organization_id)
    else:
        id_count_query = id_count_query.where(IdentifiedProfile.created_by_id == current_user.id)
    
    id_result = await db.execute(id_count_query)
    identified_used = id_result.scalar() or 0

    return {
        "trial_mode": trial_mode,
        "research": {
            "used": research_used,
            "limit": research_limit,
            "remaining": max(0, research_limit - research_used)
        },
        "classification": {
            "used": classification_used,
            "limit": classification_limit,
            "remaining": max(0, classification_limit - classification_used)
        },
        "lead_discovery": {
            "used": identified_used,
            "limit": identified_limit,
            "remaining": max(0, identified_limit - identified_used)
        }
    }
@settings_router.get("/settings/selling-profile", response_model=Optional[SellingProfileConfig])
async def get_selling_profile(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get the Global Selling Profile (Company Name, Products, etc.)
    """
    from db.models import OrganizationSettings
    from db.schemas import SellingProfileConfig
    
    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    if not settings or not settings.selling_profile_json:
        # Return default if not set
        return SellingProfileConfig(
            company_name="Your Company Name",
            description="Enterprise Solutions Provider",
            products=[]
        )
        
    try:
        data = json.loads(settings.selling_profile_json)
        return SellingProfileConfig(**data)
    except Exception as e:
        logger.error(f"Error parsing selling profile: {e}")
        return None

@settings_router.post("/settings/selling-profile", response_model=SellingProfileConfig)
async def save_selling_profile(
    profile_data: SellingProfileConfig, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Save Global Selling Profile. Admin only.
    """
    from db.models import OrganizationSettings
    
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    
    json_str = profile_data.json()
    
    if settings and (settings.organization_id == admin_user.organization_id or settings.owner_id == admin_user.id):
        settings.selling_profile_json = json_str
    else:
        settings = OrganizationSettings(
            selling_profile_json=json_str, 
            owner_id=admin_user.id,
            organization_id=admin_user.organization_id
        )
        db.add(settings)
        
    await db.commit()
    return profile_data

@settings_router.post("/settings/provision-index")
async def provision_org_index(
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Provision a new, isolated Pinecone index for this organization.
    Only one index is created per organization.
    """
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    
    if not settings:
        settings = OrganizationSettings(
            owner_id=admin_user.id,
            organization_id=admin_user.organization_id
        )
        db.add(settings)
        await db.flush() # Get the ID for naming
    
    if settings.pinecone_index_name:
        return {"status": "already_exists", "index_name": settings.pinecone_index_name}
    
    # Generate a unique name (max 45 chars)
    index_name = f"tr-{settings.id}"
    
    # Provision via KnowledgeService
    ks = KnowledgeService()
    success = await ks.create_trial_index(index_name)
    
    if success:
        settings.pinecone_index_name = index_name
        await db.commit()
        return {"status": "provisioning_started", "index_name": index_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to provision Pinecone index")
