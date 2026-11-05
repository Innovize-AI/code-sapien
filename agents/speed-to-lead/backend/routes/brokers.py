"""
Broker registry API: projects, channel partners, registration ledger, conflict resolution,
and the numbers for the dashboard (source split, leaderboard).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import crud
from db.database import get_db
from db.models import Broker, Project
from services import broker_registry as reg
from routes.guard import deny_agents

router = APIRouter(tags=["brokers"], dependencies=[Depends(deny_agents)])


# ── Projects ─────────────────────────────────────────────────────────────────

class ProjectIn(BaseModel):
    firm_id: UUID
    name: str
    location: str | None = None
    rera_number: str | None = None
    possession_date: date | None = None
    starting_price: str | None = None
    payment_plan: str | None = None
    bank_tieups: str | None = None
    validity_days: int = 60


def _project_out(p: Project) -> dict:
    return {c.key: getattr(p, c.key) for c in Project.__table__.columns}


@router.get("/projects")
async def list_projects(firm_id: UUID, db: AsyncSession = Depends(get_db)):
    return [_project_out(p) for p in await reg.list_projects(db, firm_id, active_only=False)]


@router.post("/projects")
async def create_project(body: ProjectIn, db: AsyncSession = Depends(get_db)):
    if not await crud.get_firm(db, body.firm_id):
        raise HTTPException(404, "Firm not found")
    p = Project(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _project_out(p)


# ── Brokers ──────────────────────────────────────────────────────────────────

class BrokerIn(BaseModel):
    firm_id: UUID
    name: str
    phone: str
    company: str | None = None
    rera_agent_no: str | None = None
    kind: str = "partner"              # partner | team


class BrokerPatch(BaseModel):
    status: str | None = None          # active | suspended
    name: str | None = None
    company: str | None = None


@router.get("/brokers")
async def list_brokers(firm_id: UUID, days: int = 90, db: AsyncSession = Depends(get_db)):
    """Brokers with registration, lead and visit counts (leaderboard order)."""
    rows = await reg.leaderboard(db, firm_id, days=days)
    firm = await crud.get_firm(db, firm_id)
    number = (firm.contact_phone or "").strip() if firm else ""
    digits = "".join(ch for ch in number if ch.isdigit())
    for r in rows:
        r["link"] = (f"https://wa.me/{digits}?text={r['code']}" if digits else None)
    return rows


@router.post("/brokers")
async def enrol_broker(body: BrokerIn, db: AsyncSession = Depends(get_db)):
    if not await crud.get_firm(db, body.firm_id):
        raise HTTPException(404, "Firm not found")
    try:
        b = await reg.create_broker(db, body.firm_id, body.name, body.phone,
                                    company=body.company, rera_agent_no=body.rera_agent_no,
                                    kind=body.kind)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {c.key: getattr(b, c.key) for c in Broker.__table__.columns}


@router.patch("/brokers/{broker_id}")
async def update_broker(broker_id: UUID, body: BrokerPatch, db: AsyncSession = Depends(get_db)):
    b = await db.get(Broker, broker_id)
    if not b:
        raise HTTPException(404, "Broker not found")
    if body.status is not None:
        if body.status not in ("active", "suspended"):
            raise HTTPException(400, "status must be active or suspended")
        b.status = body.status
    if body.name:
        b.name = body.name
    if body.company is not None:
        b.company = body.company
    await db.commit()
    await db.refresh(b)
    return {c.key: getattr(b, c.key) for c in Broker.__table__.columns}


# ── Registrations ────────────────────────────────────────────────────────────

class RegistrationIn(BaseModel):
    firm_id: UUID
    broker_id: UUID
    client_name: str | None = None
    client_phone: str
    project_id: UUID | None = None


class ResolveIn(BaseModel):
    action: str                         # keep_first | award_new
    note: str | None = None
    resolved_by: str | None = None


@router.get("/registrations")
async def list_registrations(
    firm_id: UUID, status: str | None = None, broker_id: UUID | None = None,
    project_id: UUID | None = None, conflicts_only: bool = False, limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    return await reg.list_registrations(db, firm_id, status=status, broker_id=broker_id,
                                        project_id=project_id, conflicts_only=conflicts_only,
                                        limit=min(limit, 500))


@router.post("/registrations")
async def create_registration(body: RegistrationIn, db: AsyncSession = Depends(get_db)):
    """Form registration by staff on behalf of a broker."""
    firm = await crud.get_firm(db, body.firm_id)
    broker = await db.get(Broker, body.broker_id)
    if not firm or not broker or broker.firm_id != firm.id:
        raise HTTPException(404, "Firm or broker not found")
    p10 = reg.phone10(body.client_phone)
    if not p10:
        raise HTTPException(400, "Enter a 10 digit client mobile number")
    project = await db.get(Project, body.project_id) if body.project_id else None
    out = await reg.register_client(db, firm=firm, broker=broker, client_phone10=p10,
                                    client_name=body.client_name, project=project, method="form")
    return {"kind": out.kind, "reference_id": out.registration.reference_id,
            "status": out.registration.status}


@router.post("/registrations/{registration_id}/resolve")
async def resolve_registration(registration_id: UUID, body: ResolveIn,
                               db: AsyncSession = Depends(get_db)):
    try:
        r = await reg.resolve_conflict(db, registration_id, body.action, body.note,
                                       body.resolved_by)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": str(r.id), "status": r.status, "conflict_state": r.conflict_state}


# ── Dashboard numbers ────────────────────────────────────────────────────────

@router.get("/dashboard/source-split")
async def source_split(firm_id: UUID, days: int = 30, db: AsyncSession = Depends(get_db)):
    return await reg.source_split(db, firm_id, days=days)


# ── Dev simulator (not registered in production) ─────────────────────────────

class BrokerMessageIn(BaseModel):
    firm_id: UUID
    from_phone: str
    text: str


dev_router = APIRouter(prefix="/dev", tags=["simulate"])


@dev_router.post("/broker-message")
async def simulate_broker_message(body: BrokerMessageIn, db: AsyncSession = Depends(get_db)):
    """Runs the broker channel without WhatsApp. Returns the reply the broker would receive,
    or {"handled": false} when the sender is an ordinary buyer."""
    if settings.is_production:
        raise HTTPException(404, "Not found")
    firm = await crud.get_firm(db, body.firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")
    r = await reg.handle_broker_message(db, firm, body.from_phone, body.text)
    if r is None:
        return {"handled": False}
    return {"handled": True, "reply": r.text, "kind": r.kind, "reference_id": r.reference_id,
            "conflict": r.conflict}
