"""
Stage advancement — LLM-based classifier using Claude structured output.

Stage can only advance forward, never go backward.
Stages: discovery -> qualification -> portfolio_match -> consideration -> booking -> conversion
"""

import logging

from workflow.state import LeadState
from services import claude
from prompts.lead_agent_prompts import get_stage_assessment_system

log = logging.getLogger(__name__)

_STAGE_ORDER = [
    "discovery",
    "qualification",
    "portfolio_match",
    "consideration",
    "booking",
    "conversion",
]


async def advance_stage(state: LeadState) -> LeadState:
    current = state.get("stage", "discovery")

    if current == "conversion":
        return state

    # Hard-wire booking->conversion when visit date is confirmed
    if state.get("visit_date_captured") and current == "booking":
        state["stage"] = "conversion"
        log.info("stage: booking->conversion (visit date captured)")
        return state

    vertical = state.get("firm_vertical")
    system_override = get_stage_assessment_system(vertical)

    try:
        assessment = await claude.assess_stage(
            message=state.get("message_text") or "",
            current_stage=current,
            config=state.get("config"),
            budget_bracket=state.get("budget_bracket"),
            turn_count=state.get("turn_count", 0),
            topics_covered=state.get("topics_covered", []),
            visit_date_captured=state.get("visit_date_captured", False),
            response_text=state.get("response_text") or "",
            system_override=system_override,
        )
    except Exception as exc:
        log.warning("stage assessment failed (%s) — keeping stage=%s", exc, current)
        return state

    new_stage = assessment.stage
    if _STAGE_ORDER.index(new_stage) > _STAGE_ORDER.index(current):
        state["stage"] = new_stage
        log.info("stage: %s->%s", current, new_stage)

    if assessment.visit_intent_detected:
        topics = state.get("topics_covered", [])
        if "visit_intent" not in topics:
            state["topics_covered"] = topics + ["visit_intent"]

    return state
