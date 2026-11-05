"""
Async CRUD operations — all runtime DB reads/writes go through here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.models import (
    Plan, Firm, FirmNumber,
    Lead, Session, ConversationLog, RetrievalLog,
    Visit, Resource, FollowupSchedule,
    BroadcastCampaign, BroadcastSend,
    InteriorProfile, RealEstateProfile, SolarProfile,
)
from workflow.state import LeadState

log = logging.getLogger(__name__)


# ── Plans ─────────────────────────────────────────────────────────────────────

async def list_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).order_by(Plan.monthly_chat_cap))
    return list(result.scalars().all())


async def get_plan(db: AsyncSession, plan_id) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()


async def get_plan_by_name(db: AsyncSession, name: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.name == name))
    return result.scalar_one_or_none()


async def seed_plans(db: AsyncSession) -> None:
    """Insert default plan tiers if they don't exist yet."""
    defaults = [
        {"name": "organic_starter", "label": "Organic Starter", "monthly_chat_cap": 75,  "price_monthly": 34999, "overage_per_chat": 15},
        {"name": "growth",          "label": "Growth",          "monthly_chat_cap": 150, "price_monthly": 49999, "overage_per_chat": 15},
        {"name": "pro",             "label": "Pro",             "monthly_chat_cap": 300, "price_monthly": 59999, "overage_per_chat": 15},
        {"name": "scale",           "label": "Scale",           "monthly_chat_cap": 500, "price_monthly": 74999, "overage_per_chat": 15},
    ]
    for d in defaults:
        existing = await get_plan_by_name(db, d["name"])
        if not existing:
            db.add(Plan(**d))
    await db.commit()


# ── Firms ─────────────────────────────────────────────────────────────────────

async def get_firm_by_wa_phone_number_id(db: AsyncSession, wa_phone_number_id: str) -> Firm | None:
    result = await db.execute(
        select(Firm).where(
            Firm.wa_phone_number_id == wa_phone_number_id,
            Firm.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_firm(db: AsyncSession, firm_id) -> Firm | None:
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    return result.scalar_one_or_none()


async def list_firms(db: AsyncSession) -> list[Firm]:
    result = await db.execute(select(Firm).order_by(Firm.created_at))
    return list(result.scalars().all())


async def create_firm(db: AsyncSession, data: dict) -> Firm:
    firm = Firm(**data)
    db.add(firm)
    await db.commit()
    await db.refresh(firm)
    return firm


async def update_firm(db: AsyncSession, firm_id, data: dict) -> None:
    data = dict(data)
    data["updated_at"] = datetime.now(timezone.utc)
    await db.execute(update(Firm).where(Firm.id == firm_id).values(**data))
    await db.commit()


async def maybe_reset_monthly_chats(db: AsyncSession, firm: Firm) -> None:
    """Reset monthly_chats_used if we've rolled into a new calendar month."""
    now = datetime.now(timezone.utc)
    reset_at = firm.usage_reset_at
    if reset_at and (reset_at.year, reset_at.month) < (now.year, now.month):
        await db.execute(
            update(Firm).where(Firm.id == firm.id).values(
                monthly_chats_used=0,
                usage_reset_at=now,
            )
        )
        await db.commit()
        firm.monthly_chats_used = 0


async def increment_monthly_chats(db: AsyncSession, firm_id) -> None:
    await db.execute(
        update(Firm).where(Firm.id == firm_id).values(
            monthly_chats_used=Firm.monthly_chats_used + 1
        )
    )
    await db.commit()


# ── Leads ─────────────────────────────────────────────────────────────────────

async def get_or_create_lead(
    db: AsyncSession,
    phone: str,
    firm_id,
    wa_name: str | None = None,
    number=None,
) -> Lead:
    result = await db.execute(
        select(Lead).where(Lead.phone == phone, Lead.firm_id == firm_id)
    )
    lead = result.scalar_one_or_none()
    if lead:
        return lead

    # Get the firm vertical to denorm into lead_type
    firm = await get_firm(db, firm_id)
    lead_type = firm.vertical if firm else None

    lead = Lead(phone=phone, wa_name=wa_name, firm_id=firm_id, lead_type=lead_type)
    if number is not None:
        # First contact came in on a person's number: that person owns the conversation and is
        # credited as the source.
        lead.number_id = number.id
        if number.person_id:
            lead.owner_id = number.person_id
            lead.broker_id = number.person_id
            lead.source = "broker"
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def update_lead(db: AsyncSession, lead_id: UUID, fields: dict) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return
    fields["last_active"] = datetime.now(timezone.utc)
    await db.execute(update(Lead).where(Lead.id == lead_id).values(**fields))
    await db.commit()


async def get_lead(db: AsyncSession, lead_id: UUID) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


# ── Vertical profiles ─────────────────────────────────────────────────────────

async def upsert_interior_profile(db: AsyncSession, lead_id, fields: dict) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = datetime.now(timezone.utc)
    stmt = pg_insert(InteriorProfile).values(lead_id=lead_id, **fields)
    update_cols = {k: stmt.excluded[k] for k in fields}
    stmt = stmt.on_conflict_do_update(index_elements=["lead_id"], set_=update_cols)
    await db.execute(stmt)
    await db.commit()


async def upsert_real_estate_profile(db: AsyncSession, lead_id, fields: dict) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = datetime.now(timezone.utc)
    stmt = pg_insert(RealEstateProfile).values(lead_id=lead_id, **fields)
    update_cols = {k: stmt.excluded[k] for k in fields}
    stmt = stmt.on_conflict_do_update(index_elements=["lead_id"], set_=update_cols)
    await db.execute(stmt)
    await db.commit()


async def upsert_solar_profile(db: AsyncSession, lead_id, fields: dict) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = datetime.now(timezone.utc)
    stmt = pg_insert(SolarProfile).values(lead_id=lead_id, **fields)
    update_cols = {k: stmt.excluded[k] for k in fields}
    stmt = stmt.on_conflict_do_update(index_elements=["lead_id"], set_=update_cols)
    await db.execute(stmt)
    await db.commit()


async def get_interior_profile(db: AsyncSession, lead_id) -> InteriorProfile | None:
    result = await db.execute(
        select(InteriorProfile).where(InteriorProfile.lead_id == lead_id)
    )
    return result.scalar_one_or_none()


async def get_real_estate_profile(db: AsyncSession, lead_id) -> RealEstateProfile | None:
    result = await db.execute(
        select(RealEstateProfile).where(RealEstateProfile.lead_id == lead_id)
    )
    return result.scalar_one_or_none()


async def get_solar_profile(db: AsyncSession, lead_id) -> SolarProfile | None:
    result = await db.execute(
        select(SolarProfile).where(SolarProfile.lead_id == lead_id)
    )
    return result.scalar_one_or_none()


# ── Sessions ──────────────────────────────────────────────────────────────────

async def get_or_create_session(db: AsyncSession, lead_id: UUID, firm_id=None) -> Session:
    result = await db.execute(
        select(Session)
        .where(Session.lead_id == lead_id, Session.ended_at.is_(None))
        .order_by(Session.started_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session:
        return session

    session = Session(lead_id=lead_id, firm_id=firm_id, context={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def save_session(db: AsyncSession, state: LeadState) -> None:
    context = {
        "history":             state.get("history", []),
        "topics_covered":      state.get("topics_covered", []),
        "resources_shared":    state.get("resources_shared", []),
        "last_resource_turn":  state.get("last_resource_turn", -1),
        "name_captured":       state.get("name_captured", False),
        "config_captured":     state.get("config_captured", False),
        "budget_captured":     state.get("budget_captured", False),
        "visit_date_captured": state.get("visit_date_captured", False),
        "education_path":      state.get("education_path", False),
        "reactivated":         state.get("reactivated", False),
        "ctwa_source_id":      state.get("ctwa_source_id"),
    }
    from uuid import UUID as _UUID
    session_id = state["session_id"]
    if isinstance(session_id, str):
        session_id = _UUID(session_id)

    await db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(
            stage=state["stage"],
            turn_count=state["turn_count"],
            context=context,
            last_message_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


# ── Conversation logs ─────────────────────────────────────────────────────────

async def message_exists(db: AsyncSession, wa_message_id: str) -> bool:
    """wamid deduplication — returns True if this message was already processed."""
    result = await db.execute(
        select(ConversationLog.id).where(ConversationLog.wa_message_id == wa_message_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def log_message(
    db: AsyncSession,
    *,
    session_id,
    lead_id,
    firm_id=None,
    direction: str,
    sender_type: str,
    message_text: str | None,
    media_type: str | None = None,
    wa_message_id: str | None = None,
    path_taken: str | None = None,
    pinecone_score: float | None = None,
    resource_sent: str | None = None,
    turn_number: int = 0,
    number_id=None,
) -> None:
    entry = ConversationLog(
        number_id=number_id,
        session_id=session_id,
        lead_id=lead_id,
        firm_id=firm_id,
        direction=direction,
        sender_type=sender_type,
        message_text=message_text,
        media_type=media_type,
        wa_message_id=wa_message_id,
        path_taken=path_taken,
        pinecone_score=pinecone_score,
        resource_sent=resource_sent,
        turn_number=turn_number,
    )
    db.add(entry)
    await db.commit()


async def get_lead_conversation(db: AsyncSession, lead_id: UUID) -> list[ConversationLog]:
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.lead_id == lead_id)
        .order_by(ConversationLog.created_at)
    )
    return result.scalars().all()


async def get_lead_retrieval_logs(db: AsyncSession, lead_id: UUID) -> list[RetrievalLog]:
    result = await db.execute(
        select(RetrievalLog)
        .where(RetrievalLog.lead_id == lead_id)
        .order_by(RetrievalLog.created_at)
    )
    return result.scalars().all()


# ── Retrieval observability ───────────────────────────────────────────────────

async def log_retrieval(db: AsyncSession, state: LeadState) -> None:
    from agents.tools import KNOWLEDGE_THRESHOLD
    entry = RetrievalLog(
        session_id=state.get("session_id"),
        lead_id=state.get("lead_id"),
        firm_id=state.get("firm_id"),
        turn_number=state.get("turn_count"),
        query_original=state.get("message_text") or "",
        knowledge_top_score=state.get("knowledge_top_score"),
        knowledge_chunks=state.get("knowledge_chunks"),
        portfolio_matches=state.get("portfolio_matches"),
        confidence_gate_passed=(state.get("knowledge_top_score") or 0) >= KNOWLEDGE_THRESHOLD,
        resource_attached=state.get("resource_to_attach") is not None,
        tools_called=state.get("tools_called") or [],
        pinecone_latency_ms=state.get("pinecone_latency_ms"),
        claude_latency_ms=state.get("claude_latency_ms"),
        total_latency_ms=state.get("total_latency_ms"),
        path_taken=state.get("path_taken") or "unknown",
    )
    db.add(entry)
    await db.commit()


# ── Resources ─────────────────────────────────────────────────────────────────

async def list_resources(db: AsyncSession, firm_id=None) -> list[Resource]:
    q = select(Resource).order_by(Resource.id)
    if firm_id is not None:
        q = q.where(Resource.firm_id == firm_id)
    result = await db.execute(q)
    return result.scalars().all()


async def upsert_resource(db: AsyncSession, r: dict) -> None:
    values = {
        "id":            r["id"],
        "title":         r["title"],
        "description":   r.get("description"),
        "resource_type": r.get("resource_type", "pdf"),
        "url":           r.get("url"),
    }
    if r.get("firm_id"):
        values["firm_id"] = r["firm_id"]

    stmt = pg_insert(Resource).values(**values).on_conflict_do_update(
        index_elements=["id"],
        set_={
            "title":         r["title"],
            "description":   r.get("description"),
            "resource_type": r.get("resource_type", "pdf"),
            "url":           r.get("url"),
            "updated_at":    datetime.now(timezone.utc),
        },
    )
    await db.execute(stmt)
    await db.commit()


async def get_resource(db: AsyncSession, resource_id: str) -> Resource | None:
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    return result.scalar_one_or_none()


async def delete_resource(db: AsyncSession, resource_id: str) -> None:
    from sqlalchemy import delete as sa_delete
    await db.execute(sa_delete(Resource).where(Resource.id == resource_id))
    await db.commit()


# ── Visits ────────────────────────────────────────────────────────────────────

async def upsert_visit(
    db: AsyncSession,
    lead_id: UUID,
    visit_date,
    firm_id=None,
    visit_time_slot: str | None = None,
    cab_pickup_address: str | None = None,
) -> None:
    result = await db.execute(select(Visit).where(Visit.lead_id == lead_id).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        await db.execute(
            update(Visit).where(Visit.lead_id == lead_id).values(
                visit_date=visit_date,
                visit_time_slot=visit_time_slot or existing.visit_time_slot,
                cab_pickup_address=cab_pickup_address or existing.cab_pickup_address,
                status="scheduled",
                updated_at=datetime.now(timezone.utc),
            )
        )
    else:
        db.add(Visit(
            lead_id=lead_id,
            firm_id=firm_id,
            visit_date=visit_date,
            visit_time_slot=visit_time_slot,
            cab_pickup_address=cab_pickup_address,
        ))
    await db.commit()


async def reschedule_visit(
    db: AsyncSession,
    lead_id: UUID,
    new_date,
    time_slot: str | None = None,
) -> None:
    await db.execute(
        update(Visit).where(Visit.lead_id == lead_id).values(
            visit_date=new_date,
            visit_time_slot=time_slot,
            status="rescheduled",
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def cancel_visit(db: AsyncSession, lead_id: UUID, reason: str | None = None) -> None:
    await db.execute(
        update(Visit).where(Visit.lead_id == lead_id).values(
            status="cancelled",
            cancellation_reason=reason,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(update(Lead).where(Lead.id == lead_id).values(lead_status="active"))
    await db.commit()


async def mark_visit_no_show(db: AsyncSession, lead_id: UUID) -> None:
    await db.execute(
        update(Visit).where(Visit.lead_id == lead_id).values(
            status="no_show",
            attended=False,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(update(Lead).where(Lead.id == lead_id).values(lead_status="active"))
    await db.commit()


async def mark_visit_attended(
    db: AsyncSession,
    lead_id: UUID,
    outcome: str | None = None,
) -> None:
    await db.execute(
        update(Visit).where(Visit.lead_id == lead_id).values(
            status="completed",
            attended=True,
            outcome=outcome,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(update(Lead).where(Lead.id == lead_id).values(lead_status="converted"))
    await db.commit()


async def list_visits(
    db: AsyncSession,
    upcoming_only: bool = True,
    firm_id=None,
    owner_id=None,
) -> list[dict]:
    q = (
        select(Visit, Lead.lead_name, Lead.lead_type, Lead.phone)
        .join(Lead, Lead.id == Visit.lead_id)
    )
    if owner_id is not None:
        q = q.where(Lead.owner_id == owner_id)
    if upcoming_only:
        q = q.where(Visit.attended.is_(None), Visit.status == "scheduled")
    if firm_id is not None:
        q = q.where(Visit.firm_id == firm_id)
    result = await db.execute(q.order_by(Visit.visit_date))

    out = []
    for row in result.all():
        visit = row[0]
        d = {c.key: getattr(visit, c.key) for c in Visit.__table__.columns}
        d["lead_name"] = row[1]
        d["lead_type"] = row[2]
        d["phone"]     = row[3]
        out.append(d)
    return out


async def set_visit_hesitation(
    db: AsyncSession,
    lead_id: UUID,
    hesitation_code: str,
) -> None:
    await db.execute(
        update(Visit).where(Visit.lead_id == lead_id).values(
            hesitation_code=hesitation_code,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


# ── Follow-up schedules ───────────────────────────────────────────────────────

async def schedule_followup(
    db: AsyncSession,
    lead_id: UUID,
    sequence: str,
    day: int,
    template_name: str,
    variables: dict,
    scheduled_at: datetime,
    firm_id=None,
) -> FollowupSchedule:
    entry = FollowupSchedule(
        lead_id=lead_id,
        firm_id=firm_id,
        sequence=sequence,
        day=day,
        template_name=template_name,
        variables=variables,
        scheduled_at=scheduled_at,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def cancel_followups(db: AsyncSession, lead_id: UUID, sequence: str | None = None) -> None:
    q = update(FollowupSchedule).where(
        FollowupSchedule.lead_id == lead_id,
        FollowupSchedule.status == "pending",
    )
    if sequence:
        q = q.where(FollowupSchedule.sequence == sequence)
    await db.execute(q.values(status="cancelled"))
    await db.commit()


async def get_pending_followups(db: AsyncSession) -> list[FollowupSchedule]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(FollowupSchedule)
        .where(FollowupSchedule.status == "pending", FollowupSchedule.scheduled_at <= now)
        .order_by(FollowupSchedule.scheduled_at)
    )
    return result.scalars().all()


async def get_pending_followups_with_phones(
    db: AsyncSession,
) -> list[tuple[FollowupSchedule, str, str | None, str | None]]:
    """Returns (followup_row, phone, meta_access_token, wa_phone_number_id) tuples."""
    from sqlalchemy import case
    now = datetime.now(timezone.utc)
    # A lead that arrived on a person's number is followed up from that same number.
    result = await db.execute(
        select(
            FollowupSchedule,
            Lead.phone,
            func.coalesce(FirmNumber.meta_access_token, Firm.meta_access_token),
            case((FirmNumber.id.isnot(None), FirmNumber.wa_phone_number_id), else_=Firm.wa_phone_number_id),
        )
        .join(Lead, Lead.id == FollowupSchedule.lead_id)
        .join(Firm, Firm.id == FollowupSchedule.firm_id, isouter=True)
        .join(FirmNumber, FirmNumber.id == Lead.number_id, isouter=True)
        .where(
            FollowupSchedule.status == "pending",
            FollowupSchedule.scheduled_at <= now,
        )
        .order_by(FollowupSchedule.scheduled_at)
    )
    return [(row[0], row[1], row[2], row[3]) for row in result.all()]


async def mark_followup_sent(db: AsyncSession, followup_id: UUID) -> None:
    await db.execute(
        update(FollowupSchedule).where(FollowupSchedule.id == followup_id).values(
            status="sent",
            sent_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def list_leads_with_stage(
    db: AsyncSession,
    firm_id=None,
    page: int = 1,
    limit: int = 20,
    lead_status: str | None = None,
    stage: str | None = None,
    ai_paused: bool | None = None,
    lead_type: str | None = None,
    search: str | None = None,
    owner_id=None,
    number_id=None,
) -> list[dict]:
    from sqlalchemy import outerjoin

    q = (
        select(
            Lead,
            Session.stage,
            Session.turn_count,
            Session.last_message_at,
        )
        .select_from(
            outerjoin(Lead, Session, (Session.lead_id == Lead.id) & Session.ended_at.is_(None))
        )
    )
    if firm_id is not None:
        q = q.where(Lead.firm_id == firm_id)
    if lead_status:
        q = q.where(Lead.lead_status == lead_status)
    if stage:
        q = q.where(Session.stage == stage)
    if ai_paused is not None:
        q = q.where(Lead.ai_paused.is_(ai_paused))
    if lead_type:
        q = q.where(Lead.lead_type == lead_type)
    if owner_id is not None:
        q = q.where(Lead.owner_id == owner_id)
    if number_id is not None:
        q = q.where(Lead.number_id == number_id)
    if search:
        pattern = f"%{search}%"
        q = q.where(Lead.lead_name.ilike(pattern) | Lead.phone.ilike(pattern))

    offset = (page - 1) * limit
    result = await db.execute(q.order_by(Lead.last_active.desc()).offset(offset).limit(limit))

    out = []
    for row in result.all():
        lead_dict = {c.key: getattr(row[0], c.key) for c in Lead.__table__.columns}
        lead_dict["stage"] = row[1]
        lead_dict["turn_count"] = row[2]
        lead_dict["last_message_at"] = row[3]
        out.append(lead_dict)
    return out


async def funnel_counts(db: AsyncSession, firm_id=None) -> dict[str, int]:
    q = (
        select(Session.stage, func.count().label("count"))
        .where(Session.ended_at.is_(None))
    )
    if firm_id is not None:
        q = q.where(Session.firm_id == firm_id)
    result = await db.execute(q.group_by(Session.stage))
    return {row.stage: row.count for row in result}


async def dashboard_stats(db: AsyncSession, firm_id=None) -> dict:
    def _filter(q, col):
        if firm_id is not None:
            return q.where(col == firm_id)
        return q

    total_messages = (await db.execute(
        _filter(
            select(func.count()).where(ConversationLog.direction == "inbound"),
            ConversationLog.firm_id,
        )
    )).scalar_one()

    ai_replies = (await db.execute(
        _filter(
            select(func.count()).where(
                ConversationLog.direction == "outbound",
                ConversationLog.sender_type == "ai",
            ),
            ConversationLog.firm_id,
        )
    )).scalar_one()

    leads_q = select(func.count()).where(Lead.lead_name.isnot(None))
    if firm_id is not None:
        leads_q = leads_q.where(Lead.firm_id == firm_id)
    leads_captured = (await db.execute(leads_q)).scalar_one()

    visits_q = select(func.count()).select_from(Visit)
    if firm_id is not None:
        visits_q = visits_q.where(Visit.firm_id == firm_id)
    visits_booked = (await db.execute(visits_q)).scalar_one()

    fallbacks_q = _filter(
        select(func.count()).where(RetrievalLog.path_taken == "fallback"),
        RetrievalLog.firm_id,
    )
    fallbacks_triggered = (await db.execute(fallbacks_q)).scalar_one()

    active_q = select(func.count()).where(Session.ended_at.is_(None))
    if firm_id is not None:
        active_q = active_q.where(Session.firm_id == firm_id)
    active_conversations = (await db.execute(active_q)).scalar_one()

    paused_q = select(func.count()).where(Lead.ai_paused.is_(True))
    if firm_id is not None:
        paused_q = paused_q.where(Lead.firm_id == firm_id)
    ai_paused_count = (await db.execute(paused_q)).scalar_one()

    return {
        "total_messages":       total_messages,
        "ai_replies":           ai_replies,
        "leads_captured":       leads_captured,
        "visits_booked":        visits_booked,
        "fallbacks_triggered":  fallbacks_triggered,
        "active_conversations": active_conversations,
        "ai_paused_count":      ai_paused_count,
    }
