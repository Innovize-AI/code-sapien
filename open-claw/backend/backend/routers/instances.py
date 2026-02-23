from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..database import get_db
from ..models import Instance, ProviderEnum
from ..services.provisioning import ProvisioningService

router = APIRouter(prefix="/instances", tags=["instances"])

class InstanceCreate(BaseModel):
    user_id: str
    provider: ProviderEnum
    region: str
    size: str

class InstanceRead(BaseModel):
    id: str
    user_id: str
    provider: ProviderEnum
    ip_address: str | None
    status: str
    region: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/", response_model=InstanceRead)
async def create_instance(data: InstanceCreate, db: AsyncSession = Depends(get_db)):
    service = ProvisioningService(db)
    try:
        instance = await service.provision_instance(
            user_id=data.user_id,
            provider_name=data.provider,
            region=data.region,
            size=data.size
        )
        return instance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[InstanceRead])
async def list_instances(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instance).where(Instance.user_id == user_id))
    return result.scalars().all()

@router.get("/{instance_id}")
async def get_instance(instance_id: str, db: AsyncSession = Depends(get_db)):
    service = ProvisioningService(db)
    status = await service.get_instance_status(instance_id)
    return {"id": instance_id, "status": status}

@router.delete("/{instance_id}")
async def delete_instance(instance_id: str, db: AsyncSession = Depends(get_db)):
    service = ProvisioningService(db)
    success = await service.delete_instance(instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Instance not found or deletion failed")
    return {"message": "Instance terminated"}
