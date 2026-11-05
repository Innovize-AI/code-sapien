from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db import crud
from routes.guard import deny_agents

router = APIRouter(prefix="/plans", tags=["plans"], dependencies=[Depends(deny_agents)])


@router.get("")
async def list_plans(db: AsyncSession = Depends(get_db)):
    plans = await crud.list_plans(db)
    return [_plan_out(p) for p in plans]


def _plan_out(p):
    return {
        "id":               str(p.id),
        "name":             p.name,
        "label":            p.label,
        "monthly_chat_cap": p.monthly_chat_cap,
        "price_monthly":    p.price_monthly,
        "overage_per_chat": p.overage_per_chat,
    }
