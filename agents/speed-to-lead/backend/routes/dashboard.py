"""
Dashboard API: read endpoints for sales staff and for agents (partners and team members).

Staff (admin, counselor) see every conversation for the firm and can filter by person or number.
An agent sees only the conversations on their own numbers. That limit is applied here, from the
signed-in account, and not from anything the browser sends.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from db.models import Broker, FirmNumber, InteriorProfile, RealEstateProfile, SolarProfile
from db.schemas import LeadOut, VisitOut
from routes.guard import agent_person_id, deny_agents, ensure_lead_access, guard
from services import auth

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(guard)])


async def _annotate(db: AsyncSession, rows: list[dict]) -> list[dict]:
    """Add the owner's name and the number's label to each lead row."""
    owner_ids = {r.get("owner_id") for r in rows if r.get("owner_id")}
    number_ids = {r.get("number_id") for r in rows if r.get("number_id")}
    owners = {}
    numbers = {}
    if owner_ids:
        owners = {b.id: b for b in (await db.execute(select(Broker).where(Broker.id.in_(owner_ids)))).scalars()}
    if number_ids:
        numbers = {n.id: n for n in (await db.execute(select(FirmNumber).where(FirmNumber.id.in_(number_ids)))).scalars()}
    # What the buyer has told us so far lives in the vertical profile tables. Add it to each row so
    # the list and the lead card can show configuration and budget.
    lead_ids = [r["id"] for r in rows if r.get("id")]
    profiles: dict = {}
    if lead_ids:
        for model, cfg_col, budget_col in (
            (InteriorProfile, "config", "budget_bracket"),
            (RealEstateProfile, "config", "budget_bracket"),
            (SolarProfile, "system_size_kw", "monthly_bill_bracket"),
        ):
            found = await db.execute(select(model).where(model.lead_id.in_(lead_ids)))
            for p in found.scalars():
                profiles[p.lead_id] = (getattr(p, cfg_col, None), getattr(p, budget_col, None),
                                       getattr(p, "scope", None) or getattr(p, "property_type", None),
                                       getattr(p, "design_style", None))
    for r in rows:
        o = owners.get(r.get("owner_id"))
        n = numbers.get(r.get("number_id"))
        r["owner_name"] = o.name if o else None
        r["owner_kind"] = o.kind if o else None
        r["number_label"] = n.label if n else None
        cfg, budget, scope, style = profiles.get(r.get("id"), (None, None, None, None))
        r["config"], r["budget_bracket"], r["scope"], r["design_style"] = cfg, budget, scope, style
    return rows


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    actor: auth.Actor | None = Depends(guard),
    db: AsyncSession = Depends(get_db),
):
    leads = await crud.list_leads_with_stage(
        db, page=page, limit=limit, lead_status=status, owner_id=agent_person_id(actor))
    return leads


@router.get("/lead/{lead_id}")
async def get_lead(lead_id: str, actor: auth.Actor | None = Depends(guard),
                   db: AsyncSession = Depends(get_db)):
    from sqlalchemy import outerjoin
    from db.models import Lead as LeadModel, Session as SessionModel
    await ensure_lead_access(db, actor, UUID(lead_id))
    q = (
        select(LeadModel, SessionModel.stage, SessionModel.turn_count, SessionModel.last_message_at)
        .select_from(
            outerjoin(LeadModel, SessionModel,
                (SessionModel.lead_id == LeadModel.id) & SessionModel.ended_at.is_(None))
        )
        .where(LeadModel.id == UUID(lead_id))
    )
    result = await db.execute(q)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead_obj = row[0]
    d = {c.key: getattr(lead_obj, c.key) for c in LeadModel.__table__.columns}
    d["stage"] = row[1]
    d["turn_count"] = row[2]
    d["last_message_at"] = row[3]
    return (await _annotate(db, [d]))[0]


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    status: str | None = None,
    stage: str | None = None,
    ai_paused: bool | None = None,
    search: str | None = None,
    firm_id: str | None = None,
    owner_id: str | None = None,
    number_id: str | None = None,
    actor: auth.Actor | None = Depends(guard),
    db: AsyncSession = Depends(get_db),
):
    forced = agent_person_id(actor)
    if forced is not None:
        # An agent is pinned to their own firm and person whatever the query says
        owner = forced
        firm_id = actor.firm_id
    else:
        owner = UUID(owner_id) if owner_id else None
    rows = await crud.list_leads_with_stage(
        db, page=page, limit=limit,
        lead_status=status, stage=stage,
        ai_paused=ai_paused, search=search,
        firm_id=firm_id,
        owner_id=owner,
        number_id=UUID(number_id) if number_id else None,
    )
    return await _annotate(db, rows)


@router.get("/visits", response_model=list[VisitOut])
async def list_visits(firm_id: str | None = None, actor: auth.Actor | None = Depends(guard),
                      db: AsyncSession = Depends(get_db)):
    forced = agent_person_id(actor)
    if forced is not None:
        firm_id = actor.firm_id
    visits = await crud.list_visits(db, upcoming_only=False, firm_id=firm_id, owner_id=forced)
    return visits


@router.get("/stats", dependencies=[Depends(deny_agents)])
async def funnel_stats(firm_id: str | None = None, db: AsyncSession = Depends(get_db)):
    counts = await crud.funnel_counts(db, firm_id=firm_id)
    stats = await crud.dashboard_stats(db, firm_id=firm_id)
    return {**stats, "funnel": counts}
