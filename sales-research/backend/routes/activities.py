from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from db.database import get_db
from db.crud import get_activities
from db.schemas import Activity as ActivitySchema

activities_router = APIRouter(tags=['Activities'])

@activities_router.get("/activities", response_model=List[ActivitySchema])
@cache(expire=60, namespace="dashboard")
async def list_activities(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Get the latest activities for the dashboard.
    """
    activities = await get_activities(db, limit=limit)
    return activities
