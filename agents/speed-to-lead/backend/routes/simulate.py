"""
Simulate route — dev-only endpoint for testing conversation flow without WhatsApp.

POST /dev/chat  {"phone": "test_001", "message": "hello", "firm_id": "<uuid>"}
-> {"response": "...", "resource": null, "stage": "discovery", "path_taken": "...", "turn": 1}

Uses the full pipeline (DB, graph, stage advance) so session state persists
across calls — keep using the same phone number to continue a conversation.
Only registered when environment != "production".

NOTE: firm_id is required for multi-tenant routing.
"""

import time
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from workflow.state import LeadState, default_state
from workflow.graph import lead_agent_graph
from workflow.stage import advance_stage
from db import crud
from db.models import ConversationLog
from db.database import SessionLocal
from agents.tools import _db_ctx
from utils.date_parser import parse_visit_date
from services import whatsapp
from services import broker_registry

log = logging.getLogger(__name__)
router = APIRouter(prefix="/dev", tags=["simulate"])


class ChatRequest(BaseModel):
    phone: str
    message: str
    firm_id: str                           # required — which firm/vertical to simulate
    wa_name: str | None = None
    number_id: str | None = None          # simulate a buyer messaging a person's registered number
    forward_to: str | None = None         # if set, forward reply to this WhatsApp number


class ChatResponse(BaseModel):
    response: str | None
    resource: dict | None
    stage: str
    path_taken: str | None
    turn: int
    firm_vertical: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def simulate_chat(req: ChatRequest):
    async with SessionLocal() as db:
        return await _run(db, req)


async def _run(db: AsyncSession, req: ChatRequest) -> ChatResponse:
    t_start = time.monotonic()

    # Load firm
    firm = await crud.get_firm(db, req.firm_id)
    if not firm:
        raise HTTPException(status_code=404, detail=f"Firm not found: {req.firm_id}")

    number = None
    if req.number_id:
        from db.models import FirmNumber
        number = await db.get(FirmNumber, UUID(req.number_id))
        if number is None or number.firm_id != firm.id:
            raise HTTPException(status_code=404, detail="Number not found for this firm")

    lead = await crud.get_or_create_lead(db, req.phone, firm_id=firm.id, wa_name=req.wa_name, number=number)
    session_row = await crud.get_or_create_session(db, lead.id, firm_id=firm.id)

    # Coded broker link: "BRK-XXXX ..." as the first words attributes the lead to that broker
    link = await broker_registry.attribute_coded_link(
        db, firm, lead, req.message, first_turn=(session_row.turn_count or 0) == 0) if number is None \
        else broker_registry.CodedLinkResult(req.message)
    if link.broker is not None or link.clean_text != req.message:
        req.message = link.clean_text or "Hi, I am interested in this project and would like the details."
        await db.refresh(lead)

    state: LeadState = await _build_state(db, req, lead, session_row, firm)

    # Avoid double-logging the same message (dev retries)
    _existing = await db.execute(
        select(ConversationLog.id)
        .where(
            ConversationLog.session_id == state["session_id"],
            ConversationLog.message_text == state["message_text"],
            ConversationLog.direction == "inbound",
        )
        .limit(1)
    )
    if not _existing.scalar_one_or_none():
        await crud.log_message(
            db,
            session_id=state["session_id"],
            lead_id=state["lead_id"],
            firm_id=firm.id,
            direction="inbound",
            sender_type="lead",
            message_text=state["message_text"],
            turn_number=state["turn_count"],
            number_id=lead.number_id,
        )

    if state["ai_paused"]:
        return ChatResponse(
            response="[ai_paused — no reply]", resource=None,
            stage=state["stage"], path_taken=None, turn=state["turn_count"],
            firm_vertical=firm.vertical,
        )

    _db_ctx.set(db)
    result: LeadState = await lead_agent_graph.ainvoke(state)
    result = await advance_stage(result)

    if result.get("handoff_to_staff"):
        await crud.update_lead(db, result["lead_id"], {"ai_paused": True})

    # Sync common lead fields
    lead_sync: dict = {}
    for field in ("lead_name", "lead_type"):
        if result.get(field):
            lead_sync[field] = result[field]
    if lead_sync:
        await crud.update_lead(db, result["lead_id"], lead_sync)

    # Upsert vertical profile
    vertical = firm.vertical
    if vertical == "interior":
        profile_fields: dict = {}
        if result.get("config"):         profile_fields["config"] = result["config"]
        if result.get("budget_bracket"): profile_fields["budget_bracket"] = result["budget_bracket"]
        if result.get("scope"):          profile_fields["scope"] = result["scope"]
        if result.get("design_style"):   profile_fields["design_style"] = result["design_style"]
        if profile_fields:
            await crud.upsert_interior_profile(db, result["lead_id"], profile_fields)
    elif vertical == "real_estate":
        profile_fields = {}
        if result.get("config"):              profile_fields["config"] = result["config"]
        if result.get("budget_bracket"):      profile_fields["budget_bracket"] = result["budget_bracket"]
        if result.get("cab_pickup_address"):  profile_fields["cab_pickup_address"] = result["cab_pickup_address"]
        if profile_fields:
            await crud.upsert_real_estate_profile(db, result["lead_id"], profile_fields)
    elif vertical == "solar":
        profile_fields = {}
        if result.get("config"):           profile_fields["system_size_kw"] = result["config"]
        if result.get("budget_bracket"):   profile_fields["monthly_bill_bracket"] = result["budget_bracket"]
        if result.get("scope"):            profile_fields["property_type"] = result["scope"]
        if result.get("roof_ownership"):   profile_fields["roof_ownership"] = result["roof_ownership"]
        if result.get("location_city"):    profile_fields["location_city"] = result["location_city"]
        if result.get("subsidy_eligible"): profile_fields["subsidy_eligible"] = result["subsidy_eligible"]
        if profile_fields:
            await crud.upsert_solar_profile(db, result["lead_id"], profile_fields)

    if result.get("visit_date_captured") and result.get("visit_date"):
        parsed = parse_visit_date(result["visit_date"])
        if parsed:
            await crud.upsert_visit(
                db,
                lead_id=result["lead_id"],
                visit_date=parsed,
                firm_id=firm.id,
                visit_time_slot=result.get("visit_time_slot"),
                cab_pickup_address=result.get("cab_pickup_address"),
            )
            await crud.update_lead(db, result["lead_id"], {"lead_status": "visit_scheduled"})

    total_ms = int((time.monotonic() - t_start) * 1000)
    result["total_latency_ms"] = total_ms

    new_history = list(result.get("history", []))
    new_history.append({"role": "user",      "content": req.message})
    new_history.append({"role": "assistant", "content": result.get("response_text") or ""})
    result["history"]    = new_history[-16:]
    result["turn_count"] = result.get("turn_count", 0) + 1

    await crud.save_session(db, result)
    await crud.update_lead(db, result["lead_id"], {"last_active": datetime.now(timezone.utc)})

    resource = result.get("resource_to_attach")
    if result.get("response_text"):
        await crud.log_message(
            db,
            session_id=result["session_id"],
            lead_id=result["lead_id"],
            firm_id=firm.id,
            direction="outbound",
            sender_type="ai",
            message_text=result["response_text"],
            path_taken=result.get("path_taken"),
            pinecone_score=result.get("knowledge_top_score"),
            resource_sent=resource["id"] if resource else None,
            turn_number=result["turn_count"],
            number_id=lead.number_id,
        )

    if result.get("path_taken") in ("knowledge", "portfolio", "fallback"):
        await crud.log_retrieval(db, result)

    # Forward to real device for testing (uses firm credentials)
    if req.forward_to and result.get("response_text"):
        fwd = "+" + req.forward_to.strip().lstrip("+")
        try:
            if resource and resource.get("type") in ("pdf", "document") and resource.get("url"):
                await whatsapp.send_document(
                    fwd, resource["url"], caption=result["response_text"],
                    access_token=firm.meta_access_token,
                    wa_phone_number_id=firm.wa_phone_number_id,
                )
            elif resource and resource.get("url"):
                combined = f"{result['response_text']}\n\n▶️ {resource['title']}\n{resource['url']}"
                await whatsapp.send_text(
                    fwd, combined,
                    access_token=firm.meta_access_token,
                    wa_phone_number_id=firm.wa_phone_number_id,
                )
            else:
                await whatsapp.send_text(
                    fwd, result["response_text"],
                    access_token=firm.meta_access_token,
                    wa_phone_number_id=firm.wa_phone_number_id,
                )
        except Exception as exc:
            log.warning("Forward to %s failed: %s", fwd, exc)

    return ChatResponse(
        response=result.get("response_text"),
        resource=resource,
        stage=result.get("stage", "discovery"),
        path_taken=result.get("path_taken"),
        turn=result["turn_count"],
        firm_vertical=firm.vertical,
    )


async def _build_state(db, req: ChatRequest, lead, session_row, firm) -> LeadState:
    state = default_state(req.phone, req.wa_name)
    state["message_type"]  = "text"
    state["message_text"]  = req.message
    state["wa_message_id"] = None
    state["referral"]      = None

    # Firm context
    state["firm_id"]               = str(firm.id)
    state["firm_vertical"]         = firm.vertical
    state["firm_display_name"]     = firm.firm_display_name or firm.name
    state["firm_visit_cta"]        = firm.visit_cta
    state["firm_meta_access_token"] = firm.meta_access_token

    # Lead fields
    state["lead_id"]       = lead.id
    state["lead_status"]   = lead.lead_status or "new"
    state["ai_paused"]     = lead.ai_paused or False
    state["wa_name"]       = req.wa_name or lead.wa_name
    state["lead_name"]     = lead.lead_name
    state["ctwa_source_id"]= lead.ctwa_source_id
    state["ctwa_config"]   = lead.ctwa_config
    state["ctwa_location"] = lead.ctwa_location
    state["broker_id"]     = str(lead.broker_id) if getattr(lead, "broker_id", None) else None
    state["project_id"]    = str(lead.project_id) if getattr(lead, "project_id", None) else None

    # Load vertical profile
    if firm.vertical == "interior":
        profile = await crud.get_interior_profile(db, lead.id)
        if profile:
            state["config"]         = profile.config
            state["budget_bracket"] = profile.budget_bracket
            state["scope"]          = profile.scope
            state["design_style"]   = profile.design_style
    elif firm.vertical == "real_estate":
        profile = await crud.get_real_estate_profile(db, lead.id)
        if profile:
            state["config"]             = profile.config
            state["budget_bracket"]     = profile.budget_bracket
            state["cab_pickup_address"] = profile.cab_pickup_address
    elif firm.vertical == "solar":
        profile = await crud.get_solar_profile(db, lead.id)
        if profile:
            state["config"]           = profile.system_size_kw
            state["budget_bracket"]   = profile.monthly_bill_bracket
            state["scope"]            = profile.property_type
            state["roof_ownership"]   = profile.roof_ownership
            state["location_city"]    = profile.location_city
            state["subsidy_eligible"] = profile.subsidy_eligible or False

    ctx = session_row.context or {}
    state["session_id"]          = session_row.id
    state["stage"]               = session_row.stage or "discovery"
    state["turn_count"]          = session_row.turn_count or 0
    state["topics_covered"]      = ctx.get("topics_covered", [])
    state["resources_shared"]    = ctx.get("resources_shared", [])
    state["last_resource_turn"]  = ctx.get("last_resource_turn", -1)
    state["name_captured"]       = ctx.get("name_captured", bool(lead.lead_name))
    state["config_captured"]     = ctx.get("config_captured", bool(state.get("config")))
    state["budget_captured"]     = ctx.get("budget_captured", bool(state.get("budget_bracket")))
    state["visit_date_captured"] = ctx.get("visit_date_captured", False)
    state["education_path"]      = ctx.get("education_path", False)
    state["reactivated"]         = ctx.get("reactivated", False)
    state["history"]             = ctx.get("history", [])

    return state
