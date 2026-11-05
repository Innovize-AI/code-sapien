"""
Resource gate — decides whether a matched resource should be attached to a reply.

Rules (both bypassed when explicit=True):
  1. Not already sent this session
  2. At least 3 turns between resource sends

explicit=True is set when SignalExtraction.wants_resource is True (lead asked for a PDF/brochure).
"""

import logging

from workflow.state import LeadState

log = logging.getLogger(__name__)

MIN_TURNS_BETWEEN_RESOURCES = 3


def should_attach(
    state: LeadState,
    candidate: dict,
    explicit: bool = False,
) -> tuple[bool, str | None]:
    """Returns (attach: bool, gate_fail_reason: str | None)."""
    resource_id = candidate.get("id", "")

    # Dedup always applies — never resend a resource already shared this session
    if resource_id in state.get("resources_shared", []):
        log.debug("Resource gate: %s — already_sent", resource_id)
        return False, "already_sent_this_session"

    # Pacing only bypassed for explicit requests
    if not explicit:
        turns_since_last = state.get("turn_count", 0) - state.get("last_resource_turn", -100)
        if turns_since_last < MIN_TURNS_BETWEEN_RESOURCES:
            reason = f"too_soon ({turns_since_last} turns since last resource)"
            log.debug("Resource gate: %s — %s", resource_id, reason)
            return False, reason

    return True, None
