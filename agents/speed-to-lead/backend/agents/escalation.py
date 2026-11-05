"""
Intent-based escalation. Some questions must reach a person even when the knowledge base
could produce an answer: negotiation and discounts, and availability of a specific unit.
The agent says it is checking with the sales head, pauses, and alerts the team.
"""

from __future__ import annotations

import re

_NEGOTIATION = re.compile(
    r"\b(discount\w*|negotiat\w*|bargain\w*|best price|final price|lowest price|"
    r"price (?:drop|cut|reduc\w*)|reduce (?:the )?price|any offers?|waive\w*|"
    r"can you do (?:it )?for)\b",
    re.IGNORECASE,
)
_UNIT = r"(?:units?|flats?|apartments?|floors?|towers?|plots?|villas?|[1-5]\s?bhk)"
_AVAIL = r"(?:available|availability|vacant|remaining|left|unsold|in stock)"
_AVAILABILITY = re.compile(
    rf"\b{_UNIT}\b.{{0,40}}\b{_AVAIL}\b|\b{_AVAIL}\b.{{0,40}}\b{_UNIT}\b|"
    r"\b(?:which|what) (?:floors?|towers?|units?|flats?) (?:are|is)\b|"
    r"\bhow many (?:units?|flats?) (?:are )?left\b",
    re.IGNORECASE,
)

REPLIES = {
    "negotiation": (
        "Pricing and offers are confirmed by our sales head. I have passed your question on, "
        "and they will reply to you here shortly."
    ),
    "availability": (
        "Unit availability changes through the day, so our sales head will confirm the exact "
        "units for you here shortly."
    ),
}


def detect_escalation(message: str | None) -> str | None:
    """Returns 'negotiation', 'availability' or None."""
    if not message:
        return None
    if _NEGOTIATION.search(message):
        return "negotiation"
    if _AVAILABILITY.search(message):
        return "availability"
    return None
