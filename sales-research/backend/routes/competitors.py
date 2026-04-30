from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from db.database import get_db
from db.schemas import Competitor, CompetitorCreate
from db import crud

router = APIRouter(prefix="/competitors", tags=["Competitors"])

from dependencies import get_current_user
from db.models import Profile

@router.post("/", response_model=Competitor)
async def create_competitor(
    competitor: CompetitorCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    return await crud.create_competitor(
        db, 
        competitor.dict(), 
        org_id=current_user.organization_id,
        user_id=str(current_user.id)
    )

@router.get("/", response_model=List[Competitor])
async def read_competitors(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    return await crud.get_competitors(
        db, 
        org_id=current_user.organization_id,
        user_id=str(current_user.id)
    )

@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    deleted = await crud.delete_competitor(db, competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"message": "Competitor deleted"}
