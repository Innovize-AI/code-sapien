from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from db.database import get_db
from db.crud import get_activities
from db.schemas import Activity as ActivitySchema

activities_router = APIRouter(tags=['Activities'])

from dependencies import get_current_user
from db.models import Profile

@activities_router.get("/activities", response_model=List[ActivitySchema])
async def list_activities(
    limit: int = 50, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get the latest activities for the dashboard.
    Isolated to the current user in Trial Mode.
    """
    activities = await get_activities(
        db, 
        limit=limit, 
        user_id=str(current_user.id), 
        org_id=current_user.organization_id
    )
    return activities
