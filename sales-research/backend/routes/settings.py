
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from db.database import get_db
from db.models import OrganizationSettings
from db.schemas import OrganizationSettingsCreate, OrganizationSettings as OrganizationSettingsSchema, IdealProfileData, IntegrationSettings

settings_router = APIRouter(tags=['Settings'])

@settings_router.get("/settings/icp", response_model=Optional[IdealProfileData])
async def get_icp(db: AsyncSession = Depends(get_db)):
    """
    Get the current organization's Ideal Customer Profile.
    """
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
async def save_icp(icp_data: IdealProfileData, db: AsyncSession = Depends(get_db)):
    """
    Save or update the Ideal Customer Profile.
    """
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    icp_json_str = icp_data.json()
    
    if settings:
        settings.icp_json = icp_json_str
    else:
        settings = OrganizationSettings(icp_json=icp_json_str)
        db.add(settings)
        
    await db.commit()
    await db.refresh(settings)
    
    return icp_data

@settings_router.get("/settings/integrations", response_model=IntegrationSettings)
async def get_integrations(db: AsyncSession = Depends(get_db)):
    """
    Get current integration settings (masked).
    """
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings:
        return IntegrationSettings()
    
    return IntegrationSettings(
        tavily_api_key=settings.tavily_api_key,
        apollo_api_key=settings.apollo_api_key
    )

@settings_router.post("/settings/integrations", response_model=IntegrationSettings)
async def save_integrations(data: IntegrationSettings, db: AsyncSession = Depends(get_db)):
    """
    Save integration keys.
    """
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if settings:
        settings.tavily_api_key = data.tavily_api_key
        settings.apollo_api_key = data.apollo_api_key
    else:
        settings = OrganizationSettings(
            tavily_api_key=data.tavily_api_key, 
            apollo_api_key=data.apollo_api_key
        )
        db.add(settings)
        
    await db.commit()
    await db.refresh(settings)
    return data
