from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from db.models import OrganizationSettings

kit_router = APIRouter(tags=['Integrations - Kit'], prefix="/integrations/kit")

@kit_router.get("/forms")
async def list_kit_forms(db: AsyncSession = Depends(get_db)):
    """
    List all forms from the configured Kit (ConvertKit) account using v3 API.
    """
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings or not settings.kit_api_key:
        raise HTTPException(status_code=400, detail="Kit API Key not configured")
    
    # v3 API endpoint
    url = "https://api.convertkit.com/v3/forms"
    params = {
        "api_key": settings.kit_api_key
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Kit API Key. Please verify your PUBLIC API Key in Kit settings.")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("message", e.response.text) if e.response.content else str(e)
            raise HTTPException(status_code=e.response.status_code, detail=f"Kit API Error: {detail}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Integration Error: {str(e)}")
