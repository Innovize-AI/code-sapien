"""
pipeline.py — entry point called by the webhook for every inbound WhatsApp message.

Processing order:
 0.  Load firm by WA phone number ID
 1.  wamid deduplication — skip if message already processed
 2.  Load lead + session from DB
 3.  Build LeadState from DB rows (including firm context + vertical profile)
 4.  Log inbound message
 5.  ai_paused guard
 6.  CTWA attribution (first message with referral payload)
 7.  Dead lead reactivation
 8.  Cancel pending follow-ups (lead re-engaged — reset the silence clock)
 9.  Invoke LangGraph: signal_extractor -> supervisor -> lead_agent
 10. Advance conversation stage (LLM-based)
 11. Visit action — cancel or reschedule detected by signal_extractor
 12. Staff handoff if low confidence
 13. Send WhatsApp reply (text or document) — uses firm's meta_access_token
 13b. Increment monthly_chats_used once per unique lead per billing month
 14. Sync new lead fields -> DB + upsert vertical profile
 15. Upsert visit + schedule follow-up sequences
 16. Persist session + conversation log
"""

import time
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from workflow.state import LeadState, default_state
from workflow.graph import lead_agent_graph
from workflow.stage import advance_stage
from db import crud
from db.database import SessionLocal
from services import whatsapp
from agents.tools import _db_ctx
from agents import ctwa as ctwa_handler
from utils.date_parser import parse_visit_date
from services import followup_sequences as fseq
from services import broker_registry
from services import numbers as numbers_svc

log = logging.getLogger(__name__)


def _dest(phone: str) -> str:
    """Staging safety: every outbound message goes to TEST_FORWARD_NUMBER, never a real person."""
    if not settings.is_production and settings.test_forward_number:
        return "+" + settings.test_forward_number.lstrip("+")
    return phone


async def process_message(raw_msg: dict, metadata: dict) -> None:
    async with SessionLocal() as db:
        await _process(db, raw_msg, metadata)


async def _process(db: AsyncSession, raw_msg: dict, metadata: dict) -> None:
    t_start = time.monotonic()
    phone = raw_msg.get("from", "")

    # ── 0. Load firm by WA phone number ID ───────────────────────────────────
    phone_number_id = (metadata or {}).get("phone_number_id")
    # A message can arrive on the firm's main number or on a number registered for a person.
    firm, number = await numbers_svc.resolve(db, phone_number_id)
    if not firm:
        log.warning("No active firm found for phone_number_id=%s — skipping", phone_number_id)
        return
    send_token, send_wa_id = numbers_svc.credentials(firm, number)
    number_id = number.id if number else None

    # ── 1. wamid deduplication ────────────────────────────────────────────────
    wa_message_id = raw_msg.get("id")
    if wa_message_id and await crud.message_exists(db, wa_message_id):
        log.info("Duplicate wamid=%s — skipping", wa_message_id)
        return

    # ── 1b. Broker channel ────────────────────────────────────────────────────
    # Enrolled channel partners write from their personal numbers. Their messages are
    # registrations and status checks, never buyer conversations. Unknown numbers that
    # try to register are rejected and recorded.
    if number is None and raw_msg.get("type", "text") == "text":
        broker_reply = await broker_registry.handle_broker_message(
            db, firm, phone, raw_msg.get("text", {}).get("body", ""), wamid=wa_message_id,
        )
        if broker_reply is not None:
            await whatsapp.send_text(
                _dest(phone), broker_reply.text,
                access_token=send_token, wa_phone_number_id=send_wa_id,
            )
            log.info("broker channel: %s -> %s", phone, broker_reply.kind)
            return

    # ── 2. Load lead + session ────────────────────────────────────────────────
    wa_name = (metadata or {}).get("wa_name")
    lead = await crud.get_or_create_lead(db, phone, firm_id=firm.id, wa_name=wa_name, number=number)
    session_row = await crud.get_or_create_session(db, lead.id, firm_id=firm.id)

    # ── 2b. Coded-link attribution ────────────────────────────────────────────
    # A buyer who taps a broker's coded link sends the broker code as the first words.
    # The lead is attributed to that broker with the buyer's own first-contact time.
    if number is None and raw_msg.get("type", "text") == "text":
        body_in = raw_msg.get("text", {}).get("body", "")
        link = await broker_registry.attribute_coded_link(
            db, firm, lead, body_in,
            first_turn=(session_row.turn_count or 0) == 0, wamid=wa_message_id,
        )
        if link.broker is not None or link.clean_text != body_in:
            raw_msg = {**raw_msg, "text": {"body": link.clean_text or
                       "Hi, I am interested in this project and would like the details."}}
            await db.refresh(lead)
            if link.notify_text and link.broker is not None:
                try:
                    await whatsapp.send_text(
                        _dest(link.broker.phone), link.notify_text,
                        access_token=send_token,
                        wa_phone_number_id=send_wa_id,
                    )
                except Exception as exc:  # broker notice is best effort
                    log.warning("broker notice failed: %s", exc)

    state: LeadState = await _build_state(db, raw_msg, lead, session_row, firm)

    # ── 3. Log inbound message ────────────────────────────────────────────────
    await crud.log_message(
        db,
        session_id=state["session_id"],
        lead_id=state["lead_id"],
        firm_id=firm.id,
        direction="inbound",
        sender_type="lead",
        message_text=state.get("message_text"),
        media_type=state.get("message_type") if state["message_type"] != "text" else None,
        wa_message_id=wa_message_id,
        turn_number=state["turn_count"],
        number_id=number_id,
    )

    # ── 4. ai_paused guard ────────────────────────────────────────────────────
    if state["ai_paused"]:
        log.info("ai_paused for %s — skipping auto-reply", phone)
        return

    # ── 4b. Monthly chat cap check ────────────────────────────────────────────
    if firm.plan_id:
        await crud.maybe_reset_monthly_chats(db, firm)
        plan = await crud.get_plan(db, firm.plan_id)
        if plan and firm.monthly_chats_used >= plan.monthly_chat_cap:
            log.warning(
                "Chat cap reached for firm=%s plan=%s used=%d cap=%d — skipping AI reply",
                firm.id, plan.name, firm.monthly_chats_used, plan.monthly_chat_cap,
            )
            return

    # ── 5. CTWA attribution ───────────────────────────────────────────────────
    referral = state.get("referral")
    if referral and not state.get("ctwa_source_id"):
        await ctwa_handler.store_attribution(db, state, referral)

    # ── 6. Dead lead reactivation ─────────────────────────────────────────────
    if state["lead_status"] in ("long_term_nurture", "broadcast_sent"):
        await crud.update_lead(db, state["lead_id"], {"lead_status": "active"})
        state["lead_status"] = "active"
        state["reactivated"] = True

    # ── 7. Cancel pending follow-ups (lead just re-engaged) ──────────────────
    await fseq.cancel_engagement_followups(db, lead.id, state["stage"])

    # Capture stage before LangGraph so we can detect advancement after
    initial_stage = state["stage"]
    first_turn    = state["turn_count"] == 0

    # ── 8. Invoke LangGraph ──────────────────────────────────────────────────
    _db_ctx.set(db)
    result: LeadState = await lead_agent_graph.ainvoke(state)

    # ── 10. Stage advancement ─────────────────────────────────────────────────
    result = await advance_stage(result)

    # ── 11. Visit action — cancel / reschedule ────────────────────────────────
    visit_action = result.get("visit_action")
    if visit_action == "cancel":
        await crud.cancel_visit(db, result["lead_id"])
        await crud.cancel_followups(db, result["lead_id"])
        result["stage"] = "booking"
        result["visit_date_captured"] = False
        result["visit_date"] = None
        result["visit_time_slot"] = None
        log.info("visit cancelled for lead=%s", phone)

    elif visit_action == "reschedule":
        new_date_str = result.get("new_visit_date")
        new_time     = result.get("new_visit_time")
        if new_date_str:
            new_date = parse_visit_date(new_date_str)
            if new_date:
                await crud.reschedule_visit(db, result["lead_id"], new_date, time_slot=new_time)
                result["visit_date"]          = new_date_str
                result["visit_time_slot"]     = new_time or result.get("visit_time_slot")
                log.info("visit rescheduled to %s for lead=%s", new_date, phone)
        else:
            # New date not yet known — drop back to booking stage to collect it
            result["stage"] = "booking"
            result["visit_date_captured"] = False
            result["visit_date"] = None
            result["visit_time_slot"] = None
            log.info("reschedule intent detected — awaiting new date for lead=%s", phone)

    # ── 12. Staff handoff ─────────────────────────────────────────────────────
    if result.get("handoff_to_staff"):
        await crud.update_lead(db, result["lead_id"], {"ai_paused": True})
        log.info("ai_paused=True set for %s — low confidence, staff to take over", phone)

    # ── 13. Send WhatsApp reply ───────────────────────────────────────────────
    resource = result.get("resource_to_attach")
    response_text = result.get("response_text") or ""

    # Use firm's access token and phone number ID
    firm_access_token = send_token
    firm_phone_number_id = send_wa_id

    send_to = phone
    if not settings.is_production and settings.test_forward_number:
        send_to = "+" + settings.test_forward_number.lstrip("+")
        log.info("Staging: redirecting reply %s -> %s", phone, send_to)

    if not response_text:
        log.warning("No response_text for %s path=%s", phone, result.get("path_taken"))
    elif resource and resource.get("type") in ("pdf", "document") and resource.get("url"):
        await whatsapp.send_document(
            send_to,
            resource["url"],
            caption=response_text,
            access_token=firm_access_token,
            wa_phone_number_id=firm_phone_number_id,
        )
    elif resource and resource.get("type") in ("youtube", "video") and resource.get("url"):
        combined = f"{response_text}\n\n▶️ {resource['title']}\n{resource['url']}"
        await whatsapp.send_text(
            send_to,
            combined,
            access_token=firm_access_token,
            wa_phone_number_id=firm_phone_number_id,
        )
    else:
        await whatsapp.send_text(
            send_to,
            response_text,
            access_token=firm_access_token,
            wa_phone_number_id=firm_phone_number_id,
        )

    # Increment chat counter once per unique lead per billing month:
    # - first turn ever in this session (new lead), OR
    # - lead re-engaging after the monthly usage reset (returning lead, new month)
    if firm.plan_id and response_text:
        is_new_conversation = state["turn_count"] == 0
        is_new_month_for_lead = (
            session_row.last_message_at is not None
            and firm.usage_reset_at is not None
            and session_row.last_message_at < firm.usage_reset_at
        )
        if is_new_conversation or is_new_month_for_lead:
            await crud.increment_monthly_chats(db, firm.id)

    # ── 14. Sync lead fields -> DB + vertical profile ─────────────────────────
    lead_sync: dict = {}
    for field in ("lead_name", "lead_type"):
        if result.get(field):
            lead_sync[field] = result[field]
    if lead_sync:
        await crud.update_lead(db, result["lead_id"], lead_sync)

    # Upsert vertical profile
    vertical = result.get("firm_vertical")
    if vertical == "interior":
        profile_fields: dict = {}
        if result.get("config"):          profile_fields["config"] = result["config"]
        if result.get("budget_bracket"):  profile_fields["budget_bracket"] = result["budget_bracket"]
        if result.get("scope"):           profile_fields["scope"] = result["scope"]
        if result.get("design_style"):    profile_fields["design_style"] = result["design_style"]
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

    # ── 15. Upsert visit + schedule follow-up sequences ──────────────────────
    final_stage = result["stage"]

    visit_just_booked = (
        result.get("visit_date_captured")
        and result.get("visit_date")
        and not state.get("visit_date_captured")   # wasn't captured before this turn
    )

    parsed_date = None
    if result.get("visit_date_captured") and result.get("visit_date"):
        parsed_date = parse_visit_date(result["visit_date"])
        if parsed_date:
            await crud.upsert_visit(
                db,
                lead_id=result["lead_id"],
                visit_date=parsed_date,
                firm_id=firm.id,
                visit_time_slot=result.get("visit_time_slot"),
                cab_pickup_address=result.get("cab_pickup_address"),
            )
            await crud.update_lead(db, result["lead_id"], {"lead_status": "visit_scheduled"})

    # Follow-up sequence scheduling
    if visit_just_booked and parsed_date:
        # Visit confirmed — cancel silence-clock sequences and send reminders
        await crud.cancel_followups(db, result["lead_id"], sequence="pre_qualification")
        await crud.cancel_followups(db, result["lead_id"], sequence="pre_visit")
        await fseq.schedule_visit_reminders(
            db,
            lead_id=result["lead_id"],
            lead_name=result.get("lead_name"),
            visit_date=parsed_date,
            visit_time_slot=result.get("visit_time_slot"),
            lead_type=result.get("firm_vertical"),
            firm_id=firm.id,
        )

    elif first_turn:
        # First agent reply ever — start the pre-qualification silence clock
        await fseq.schedule_pre_qualification(
            db,
            lead_id=result["lead_id"],
            stage=final_stage,
            lead_name=result.get("lead_name"),
            config=result.get("config"),
            firm_id=firm.id,
        )

    elif (
        initial_stage in ("discovery", "qualification", "portfolio_match")
        and final_stage in ("consideration", "booking")
    ):
        # Lead just qualified — switch to the pre-visit silence clock
        await fseq.schedule_pre_visit(
            db,
            lead_id=result["lead_id"],
            stage=final_stage,
            lead_name=result.get("lead_name"),
            firm_id=firm.id,
        )

    # ── 16. Persist session + history ─────────────────────────────────────────
    total_ms = int((time.monotonic() - t_start) * 1000)
    result["total_latency_ms"] = total_ms

    new_history = list(result.get("history", []))
    new_history.append({"role": "user",      "content": state.get("message_text") or ""})
    new_history.append({"role": "assistant", "content": result.get("response_text") or ""})
    result["history"]    = new_history[-16:]   # cap at 8 turns
    result["turn_count"] = result.get("turn_count", 0) + 1

    await crud.save_session(db, result)
    await crud.update_lead(db, result["lead_id"], {"last_active": datetime.now(timezone.utc)})

    # ── 17. Log outbound + retrieval ──────────────────────────────────────────
    if response_text:
        await crud.log_message(
            db,
            session_id=result["session_id"],
            lead_id=result["lead_id"],
            firm_id=firm.id,
            direction="outbound",
            sender_type="ai",
            message_text=response_text,
            path_taken=result.get("path_taken"),
            pinecone_score=result.get("knowledge_top_score"),
            resource_sent=resource["id"] if resource else None,
            turn_number=result["turn_count"],
            number_id=number_id,
        )

    if result.get("path_taken") in ("knowledge", "portfolio", "fallback"):
        await crud.log_retrieval(db, result)


# ── State builder ─────────────────────────────────────────────────────────────

async def _build_state(db, raw_msg: dict, lead, session_row, firm) -> LeadState:
    msg_type = raw_msg.get("type", "text")
    state = default_state(lead.phone, lead.wa_name)

    state["message_type"]  = msg_type
    state["wa_message_id"] = raw_msg.get("id")
    state["referral"]      = raw_msg.get("referral")

    if msg_type == "text":
        state["message_text"] = raw_msg.get("text", {}).get("body", "")
    elif msg_type == "audio":
        state["message_text"] = None
    elif msg_type in ("image", "document"):
        media = raw_msg.get(msg_type, {})
        state["message_text"] = media.get("caption")   # caption if any

    # ── Firm context ──────────────────────────────────────────────────────────
    state["firm_id"]                = str(firm.id)
    state["firm_vertical"]          = firm.vertical
    state["firm_display_name"]      = firm.firm_display_name or firm.name
    state["firm_visit_cta"]         = firm.visit_cta
    state["firm_meta_access_token"] = firm.meta_access_token
    state["firm_contact_phone"]     = firm.contact_phone
    state["firm_contact_email"]     = firm.contact_email

    # ── Lead common fields ────────────────────────────────────────────────────
    state["lead_id"]           = lead.id
    state["lead_status"]       = lead.lead_status or "new"
    state["ai_paused"]         = lead.ai_paused or False
    state["wa_name"]           = lead.wa_name
    state["lead_name"]         = lead.lead_name
    state["is_qualified"]      = lead.is_qualified or False
    state["ctwa_source_id"]    = lead.ctwa_source_id
    state["ctwa_config"]       = lead.ctwa_config
    state["ctwa_location"]     = lead.ctwa_location
    state["broker_id"]         = str(lead.broker_id) if getattr(lead, "broker_id", None) else None
    state["project_id"]        = str(lead.project_id) if getattr(lead, "project_id", None) else None

    # ── Load vertical profile ─────────────────────────────────────────────────
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
            state["config"]              = profile.config
            state["budget_bracket"]      = profile.budget_bracket
            state["cab_pickup_address"]  = profile.cab_pickup_address

    elif firm.vertical == "solar":
        profile = await crud.get_solar_profile(db, lead.id)
        if profile:
            state["config"]            = profile.system_size_kw
            state["budget_bracket"]    = profile.monthly_bill_bracket
            state["scope"]             = profile.property_type
            state["roof_ownership"]    = profile.roof_ownership
            state["location_city"]     = profile.location_city
            state["subsidy_eligible"]  = profile.subsidy_eligible or False

    # ── Session state ─────────────────────────────────────────────────────────
    ctx = session_row.context or {}
    state["session_id"]        = session_row.id
    state["stage"]             = session_row.stage or "discovery"
    state["turn_count"]        = session_row.turn_count or 0
    state["topics_covered"]    = ctx.get("topics_covered", [])
    state["resources_shared"]  = ctx.get("resources_shared", [])
    state["last_resource_turn"]= ctx.get("last_resource_turn", -1)
    state["name_captured"]     = ctx.get("name_captured", bool(lead.lead_name))
    state["config_captured"]   = ctx.get("config_captured", bool(state.get("config")))
    state["budget_captured"]   = ctx.get("budget_captured", bool(state.get("budget_bracket")))
    state["visit_date_captured"] = ctx.get("visit_date_captured", False)
    state["education_path"]    = ctx.get("education_path", False)
    state["reactivated"]       = ctx.get("reactivated", False)
    state["history"]           = ctx.get("history", [])

    return state
