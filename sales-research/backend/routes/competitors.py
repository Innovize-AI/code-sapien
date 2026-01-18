from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from db.database import get_db
from db.schemas import Competitor, CompetitorCreate
from db import crud

router = APIRouter(prefix="/competitors", tags=["Competitors"])

@router.post("/", response_model=Competitor)
async def create_competitor(competitor: CompetitorCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_competitor(db, competitor.dict())

@router.get("/", response_model=List[Competitor])
async def read_competitors(db: AsyncSession = Depends(get_db)):
    return await crud.get_competitors(db)

@router.delete("/{competitor_id}")
async def delete_competitor(competitor_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_competitor(db, competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"message": "Competitor deleted"}
