"""
AI summary of a lead's conversation, for the staff who pick it up.

The summary is cached per lead and regenerated only when the message count has changed, so
opening the tab twice costs one model call. It is built only from the conversation and the
lead's recorded facts. It never invents details.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Broker, ConversationLog, Lead, LeadSummary, Project, RealEstateProfile, Session, Visit,
)
from services import claude

log = logging.getLogger(__name__)

MAX_MESSAGES = 60          # most recent messages sent to the model
MAX_CHARS = 600            # per message


class LeadSummaryOut(BaseModel):
    headline: str = Field(description="One sentence: who the buyer is and what they want. Under 25 words.")
    intent: Literal["hot", "warm", "cold"] = Field(
        description="hot: asked for a visit, price or next step. warm: engaged, still comparing. cold: little engagement or no reply."
    )
    what_they_want: list[str] = Field(
        description=(
            "Up to 5 short facts the buyer themself wrote: configuration, budget, location, timeline, loan, "
            "purpose. Take these only from WHAT THE BUYER WROTE. If the buyer only asked questions and stated "
            "no requirement, return an empty list."
        )
    )
    concerns: list[str] = Field(
        description="Up to 4 questions, objections or worries the buyer raised. Empty if none."
    )
    where_it_stands: str = Field(
        description="One or two sentences: what has happened so far and the current stage."
    )
    next_action: str = Field(
        description="One concrete next step for the sales team, for example confirm a visit time or answer a pricing question."
    )


SYSTEM = (
    "You write a short handover summary of a WhatsApp conversation between a real estate buyer and a "
    "developer's assistant, for the sales team member who is about to pick it up. "
    "Use only what is in the conversation and the recorded facts. Never invent a number, date, name or promise. "
    "If something was not said, leave it out. "
    "Only attribute to the buyer what the buyer wrote. A price, size or date that the assistant or staff "
    "quoted is information given to the buyer, not the buyer's budget or requirement. "
    "The recorded facts are captured automatically and can be wrong, so prefer the buyer's own words when they differ. "
    "Write in plain, direct sentences. No em-dashes. No exclamation marks. No filler. "
    "Say 'buyer' for the person. Money in lakhs or crores as they said it."
)


def _label(row: ConversationLog) -> str:
    if row.sender_type == "lead":
        return "Buyer"
    if row.sender_type == "admin":
        return "Staff"
    return "Assistant"


def build_transcript(rows: list[ConversationLog]) -> str:
    lines = []
    for r in rows[-MAX_MESSAGES:]:
        text = (r.message_text or "").strip().replace("\n", " ")
        if not text:
            continue
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "..."
        lines.append(f"{_label(r)}: {text}")
    return "\n".join(lines)


async def _facts(db: AsyncSession, lead: Lead) -> str:
    parts: list[str] = []
    if lead.lead_name or lead.wa_name:
        parts.append(f"Name: {lead.lead_name or lead.wa_name}")
    parts.append(f"Lead status: {lead.lead_status}")
    parts.append("Assistant paused, staff in control" if lead.ai_paused else "Assistant is handling the chat")

    stage = (await db.execute(
        select(Session.stage).where(Session.lead_id == lead.id).order_by(Session.started_at.desc()).limit(1)
    )).scalar_one_or_none()
    if stage:
        parts.append(f"Stage: {stage}")

    profile = (await db.execute(
        select(RealEstateProfile).where(RealEstateProfile.lead_id == lead.id))).scalar_one_or_none()
    if profile:
        if profile.config:
            parts.append(f"Configuration: {profile.config}")
        if profile.budget_bracket:
            parts.append(f"Budget bracket: {profile.budget_bracket}")

    if lead.broker_id:
        broker = await db.get(Broker, lead.broker_id)
        if broker:
            parts.append(f"Came through channel partner {broker.name}"
                         f"{' of ' + broker.company if broker.company else ''}")
    elif lead.ctwa_source_id:
        parts.append("Came from a Click-to-WhatsApp ad")
    if lead.project_id:
        project = await db.get(Project, lead.project_id)
        if project:
            parts.append(f"Project: {project.name}")

    visit = (await db.execute(
        select(Visit).where(Visit.lead_id == lead.id).order_by(Visit.visit_date.desc()).limit(1)
    )).scalar_one_or_none()
    if visit:
        parts.append(f"Visit {visit.status or 'scheduled'} for {visit.visit_date.isoformat()}"
                     f"{' ' + visit.visit_time_slot if visit.visit_time_slot else ''}")
    return "\n".join(parts)


async def _count(db: AsyncSession, lead_id: UUID) -> int:
    return (await db.execute(
        select(func.count()).select_from(ConversationLog).where(ConversationLog.lead_id == lead_id)
    )).scalar_one()


async def get_summary(db: AsyncSession, lead_id: UUID, refresh: bool = False) -> dict:
    """Returns {'empty': True} when there is nothing to summarise, otherwise the summary fields
    plus message_count, updated_at and cached (whether it came from the cache)."""
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError("Lead not found")

    count = await _count(db, lead_id)
    if count == 0:
        return {"empty": True}

    cached = await db.get(LeadSummary, lead_id)
    if cached and cached.message_count == count and not refresh:
        return {**cached.summary, "message_count": count, "updated_at": cached.updated_at,
                "cached": True, "empty": False}

    rows = list((await db.execute(
        select(ConversationLog).where(ConversationLog.lead_id == lead_id)
        .order_by(ConversationLog.created_at))).scalars())
    buyer_only = build_transcript([r for r in rows if r.sender_type == "lead"])
    prompt = (
        f"RECORDED FACTS\n{await _facts(db, lead)}\n\n"
        f"CONVERSATION (oldest first)\n{build_transcript(rows)}\n\n"
        "WHAT THE BUYER WROTE (the only source for 'what_they_want' and 'concerns')\n"
        f"{buyer_only}"
    )

    client = claude._client_or_raise()
    response = await client.aio.models.generate_content(
        model=claude._MODEL_STRUCT,
        contents=prompt,
        config=claude._gen_config(900, 0.2, SYSTEM, schema=LeadSummaryOut),
    )
    out = LeadSummaryOut.model_validate_json(claude._strip_json_markdown(response.text))
    data = out.model_dump()
    now = datetime.now(timezone.utc)

    if cached:
        cached.summary, cached.message_count, cached.model, cached.updated_at = (
            data, count, claude._MODEL_STRUCT, now)
    else:
        db.add(LeadSummary(lead_id=lead_id, summary=data, message_count=count,
                           model=claude._MODEL_STRUCT, updated_at=now))
    await db.commit()
    return {**data, "message_count": count, "updated_at": now, "cached": False, "empty": False}
