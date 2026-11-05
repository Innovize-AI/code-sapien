"""
Signal extractor node — runs on every inbound message before the lead agent.

Extracts structured lead fields from the message (name, config, budget, lead_type,
visit date, education_path, etc.) via Claude structured output, merges them into
state, and persists any new fields to the DB.
"""

import logging
from datetime import datetime, timezone

from workflow.state import LeadState
from services import claude
from db import crud
from agents.tools import _db_ctx

_CANCEL_RESCHEDULE_KEYWORDS = {
    "cancel", "reschedule", "can't come", "cannot come", "won't make it",
    "can't make it", "shift", "postpone", "change", "move", "different day",
    "something came up", "not coming", "unable to come",
}

log = logging.getLogger(__name__)


async def signal_extractor_node(state: LeadState) -> LeadState:
    message = state.get("message_text")
    if not message:
        return state

    # ── Visit action detection (cancel / reschedule) ──────────────────────────
    # Only run when a visit is already booked AND the message looks relevant.
    if state.get("visit_date_captured") and state.get("visit_date"):
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in _CANCEL_RESCHEDULE_KEYWORDS):
            try:
                action_result = await claude.extract_visit_action(
                    message=message,
                    booked_date=state["visit_date"],
                )
                if action_result.action:
                    state["visit_action"] = action_result.action
                    if action_result.new_date:
                        state["new_visit_date"] = action_result.new_date
                    if action_result.new_time:
                        state["new_visit_time"] = action_result.new_time
                    log.info(
                        "visit_action=%s new_date=%s for lead=%s",
                        action_result.action, action_result.new_date, state.get("phone"),
                    )
            except Exception as exc:
                log.warning("extract_visit_action failed: %s", exc)

    # ── Standard signal extraction ────────────────────────────────────────────
    context_hint = _last_agent_message(state)
    signals = await claude.extract_signals(message, context_hint=context_hint)

    state = _apply_signals(state, signals)

    try:
        db = _db_ctx.get()
        lead_updates = _signals_to_lead_fields(signals, state)
        if lead_updates and state.get("lead_id"):
            await crud.update_lead(db, state["lead_id"], lead_updates)
    except LookupError:
        log.warning("signal_extractor: _db_ctx not set, skipping DB persist")

    return state


# ── Helpers ───────────────────────────────────────────────────────────────────

def _last_agent_message(state: LeadState) -> str:
    history = state.get("history", [])
    last_q = next(
        (m["content"] for m in reversed(history) if m["role"] == "assistant"),
        "",
    )
    return f"Agent asked: {last_q[:120]}" if last_q else ""


def _apply_signals(state: LeadState, signals: dict) -> LeadState:
    """Merge extracted signals into state — never overwrites existing captured values."""

    if signals.get("lead_name") and not state.get("lead_name"):
        state["lead_name"] = signals["lead_name"]
        state["name_captured"] = True

    if signals.get("lead_type") and not state.get("lead_type"):
        state["lead_type"] = signals["lead_type"]

    # Use firm_vertical as the authoritative vertical source; fall back to lead_type
    is_solar = (state.get("firm_vertical") or state.get("lead_type")) == "solar"

    if signals.get("config") and not state.get("config"):
        state["config"] = signals["config"]
        state["config_captured"] = True

    # Solar: property type maps to scope field
    if is_solar and signals.get("property_type") and not state.get("scope"):
        state["scope"] = signals["property_type"]
        # Derive system size from property type if not already set
        if not state.get("config") and signals["property_type"] == "commercial":
            state["config_captured"] = False  # still need to ask

    # Solar: monthly bill maps to budget_bracket
    if is_solar and signals.get("monthly_bill") and not state.get("budget_bracket"):
        state["budget_bracket"] = _normalise_monthly_bill(signals["monthly_bill"])
        state["budget_captured"] = True

    # RE/ID: budget in lakhs/crores maps to budget_bracket
    if not is_solar and signals.get("budget") and not state.get("budget_bracket"):
        vertical = state.get("firm_vertical") or "interior"
        state["budget_bracket"] = _normalise_budget(signals["budget"], vertical=vertical)
        state["budget_captured"] = True

    if signals.get("scope") and not state.get("scope"):
        state["scope"] = signals["scope"]

    if signals.get("education_path") and not state.get("education_path"):
        state["education_path"] = True

    # Solar-specific fields
    if is_solar:
        if signals.get("roof_ownership") and not state.get("roof_ownership"):
            state["roof_ownership"] = signals["roof_ownership"]
            if signals["roof_ownership"] == "rented":
                state["is_qualified"] = False
                state["disqualified_reason"] = "rented_roof"

        if signals.get("location_city") and not state.get("location_city"):
            state["location_city"] = signals["location_city"]

        # Compute PM Surya Ghar subsidy eligibility
        if not state.get("subsidy_eligible") and state.get("scope") == "residential":
            cfg = state.get("config", "")
            if cfg in ("1kW", "3kW", "5kW", "10kW"):
                state["subsidy_eligible"] = True

    if signals.get("visit_date") and not state.get("visit_date"):
        state["visit_date"] = signals["visit_date"]
        state["visit_date_captured"] = True

    if signals.get("visit_time") and not state.get("visit_time_slot"):
        state["visit_time_slot"] = signals["visit_time"]

    if signals.get("cab_pickup_address") and not state.get("cab_pickup_address"):
        state["cab_pickup_address"] = signals["cab_pickup_address"]

    state["resource_explicitly_requested"] = bool(signals.get("wants_resource", False))
    state["is_knowledge_question"] = bool(signals.get("is_knowledge_question", False))

    return state


def _normalise_monthly_bill(raw: str) -> str:
    """Map a solar monthly electricity bill mention to a bracket slug."""
    r = raw.lower().replace(",", "").replace(" ", "").replace("rs", "").replace("₹", "").replace("/month", "").replace("pm", "")
    try:
        val = float(r.replace("k", "")) * (1000 if "k" in r else 1)
    except ValueError:
        return "unknown"
    if val < 2000:
        return "under_2k"
    if val <= 5000:
        return "2k-5k"
    if val <= 10000:
        return "5k-10k"
    return "10k+"


def _normalise_budget(raw: str, vertical: str = "interior") -> str:
    """Map a free-text budget mention to a bracket slug.

    Handles ranges like "35-40 lakhs" or "1.5-2 crore" by taking the lower
    bound number while preserving the unit from anywhere in the string.
    """
    r = raw.lower().replace(",", "").replace(" ", "")

    # Determine unit from the FULL string (not just after splitting)
    if "crore" in r or "cr" in r:
        unit = "cr"
    elif "lakh" in r or "l" in r:
        unit = "lakh"
    else:
        return "unknown"

    # Strip all unit text to get the numeric part, then take lower bound of range
    num_str = (
        r.replace("crore", "").replace("cr", "")
         .replace("lakhs", "").replace("lakh", "")
         .replace("l", "")
         .strip("-")
    )
    num_str = num_str.split("-")[0]  # lower bound of range e.g. "1.5" from "1.5-2"

    try:
        val = float(num_str)
    except ValueError:
        return "unknown"

    lakhs = val * 100 if unit == "cr" else val

    if vertical == "real_estate":
        if lakhs < 50:
            return "under_50L"
        if lakhs < 100:
            return "50L-1Cr"
        if lakhs < 200:
            return "1Cr-2Cr"
        return "2Cr+"

    # Interior design brackets
    if lakhs < 5:
        return "under_5L"
    if lakhs <= 10:
        return "5-10L"
    if lakhs <= 20:
        return "10-20L"
    return "20L+"


def _signals_to_lead_fields(signals: dict, state: LeadState) -> dict:
    """
    Map extracted signals to Lead DB column names for crud.update_lead().
    Only includes fields that still live on the leads table.
    Vertical-specific fields (config, budget_bracket, scope, etc.) are
    now stored in profile tables and upserted by the pipeline after each turn.
    """
    updates: dict = {}
    if signals.get("lead_name"):
        updates["lead_name"] = signals["lead_name"]
    if signals.get("lead_type"):
        updates["lead_type"] = signals["lead_type"]
    if signals.get("visit_date"):
        updates["visit_date"] = signals["visit_date"]
    if signals.get("visit_time"):
        updates["visit_time_slot"] = signals["visit_time"]

    # Mark lead as captured when core fields are present
    if state.get("lead_name") and state.get("visit_date_captured"):
        updates["lead_captured_at"] = datetime.now(timezone.utc)
        updates["lead_status"] = "visit_scheduled"

    return updates
