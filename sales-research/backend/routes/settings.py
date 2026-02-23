
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from db.database import get_db
from db.models import OrganizationSettings, Profile
from db.schemas import OrganizationSettingsCreate, OrganizationSettings as OrganizationSettingsSchema, IdealProfileData, IntegrationSettings, SellingProfileConfig
from dependencies import get_current_user, require_admin

settings_router = APIRouter(tags=['Settings'])

@settings_router.get("/settings/icp", response_model=Optional[IdealProfileData])
async def get_icp(
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

    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings or not settings.icp_json:
        return None
        
    try:
        data = json.loads(settings.icp_json)
        return IdealProfileData(**data)
    except:
        return None

@settings_router.post("/settings/icp", response_model=IdealProfileData)
async def save_icp(
    icp_data: IdealProfileData, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Save ICP. Admins save to Global, Reps save to their Personal Override.
    """
    if current_user.role == 'admin':
        # Admin saves to Global
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        icp_json_str = icp_data.json()
        if settings:
            settings.icp_json = icp_json_str
        else:
            settings = OrganizationSettings(icp_json=icp_json_str)
            db.add(settings)
        await db.commit()
    else:
        # Rep saves to personal override
        from db.crud import upsert_user_settings
        await upsert_user_settings(db, str(current_user.id), {"icp_json": icp_data.json()})
    
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
    # ... (existing admin logic)
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings:
        return IntegrationSettings()
    
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
    )


@settings_router.post("/settings/integrations", response_model=IntegrationSettings)
async def save_integrations(
    data: IntegrationSettings, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if settings:
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
    else:
        settings = OrganizationSettings(
            tavily_api_key=data.tavily_api_key, 
            apollo_api_key=data.apollo_api_key,
            email_config=data.email_config,
            integrations_config=data.integrations_config,
            kit_api_key=data.kit_api_key,
            kit_api_secret=data.kit_api_secret,
            user_linkedin_url=data.user_linkedin_url,
            company_linkedin_url=data.company_linkedin_url,
            slack_webhook_url=data.slack_webhook_url,
            discovery_keywords=data.discovery_keywords,
            apollo_search_config=data.apollo_search_config,
            hubspot_access_token=data.hubspot_access_token,
            hubspot_sync_enabled=data.hubspot_sync_enabled,
        )

        db.add(settings)
        
    await db.commit()
    await db.refresh(settings)
    return data

@settings_router.get("/settings/onboarding-status")
async def get_onboarding_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    return {"complete": bool(settings.onboarding_complete) if settings else False}

@settings_router.post("/settings/onboarding-complete")
async def set_onboarding_complete(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    if settings:
        settings.onboarding_complete = 1
        await db.commit()
    return {"status": "success"}
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
    
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings or not settings.selling_profile_json:
        # Return default if not set
        return SellingProfileConfig(
            company_name="Innovize AI",
            description="Specialized AI Transformation",
            products=[]
        )
        
    try:
        data = json.loads(settings.selling_profile_json)
        return SellingProfileConfig(**data)
    except Exception as e:
        print(f"Error parsing selling profile: {e}")
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
    
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    json_str = profile_data.json()
    
    if settings:
        settings.selling_profile_json = json_str
    else:
        settings = OrganizationSettings(selling_profile_json=json_str)
        db.add(settings)
        
    await db.commit()
    return profile_data
