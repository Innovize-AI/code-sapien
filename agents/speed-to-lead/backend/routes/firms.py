"""
Firms CRUD API — manage multi-tenant firm records.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from db.database import get_db
from db import crud
from routes.plans import _plan_out
from routes.guard import deny_agents, guard
from services import auth

router = APIRouter(prefix="/firms", tags=["firms"], dependencies=[Depends(guard)])


@router.get("", dependencies=[Depends(deny_agents)])
async def list_firms(db: AsyncSession = Depends(get_db)):
    firms = await crud.list_firms(db)
    return [_firm_out(f) for f in firms]


@router.post("", dependencies=[Depends(deny_agents)])
async def create_firm(data: dict, db: AsyncSession = Depends(get_db)):
    firm = await crud.create_firm(db, data)
    return _firm_out(firm)


@router.get("/{firm_id}")
async def get_firm(firm_id: UUID, actor: auth.Actor | None = Depends(guard),
                   db: AsyncSession = Depends(get_db)):
    firm = await crud.get_firm(db, firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")
    if actor is not None and actor.is_agent:
        # An agent sees only their own firm, and never its Meta credentials or plan
        if actor.firm_id != str(firm.id):
            raise HTTPException(403, "Your account cannot use this")
        return _firm_out(firm)
    plan = await crud.get_plan(db, firm.plan_id) if firm.plan_id else None
    return {**_firm_out(firm), **_firm_sensitive(firm), "plan": _plan_out(plan) if plan else None}


@router.patch("/{firm_id}", dependencies=[Depends(deny_agents)])
async def update_firm(firm_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    firm = await crud.get_firm(db, firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")
    await crud.update_firm(db, firm_id, data)
    return {"ok": True}


def _firm_out(f):
    return {
        "id":                   str(f.id),
        "name":                 f.name,
        "vertical":             f.vertical,
        "is_active":            f.is_active,
        "plan_id":              str(f.plan_id) if f.plan_id else None,
        "monthly_chats_used":   f.monthly_chats_used or 0,
        "wa_phone_number_id":   f.wa_phone_number_id,
        "firm_display_name":    f.firm_display_name,
        "visit_cta":            f.visit_cta,
        "booking_link":         f.booking_link,
        "maps_link":            f.maps_link,
        "fallback_alert_email": f.fallback_alert_email,
        "created_at":           f.created_at.isoformat() if f.created_at else None,
    }


def _firm_sensitive(f):
    return {
        "meta_access_token":         f.meta_access_token,
        "meta_webhook_verify_token": f.meta_webhook_verify_token,
        "meta_app_secret":           f.meta_app_secret,
    }
