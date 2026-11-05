"""
CTWA (Click-to-WhatsApp) attribution — stores ad referral on the lead.

Also extracts config/location from the ad headline if present
(e.g. "3BHK in Whitefield" → ctwa_config="3BHK", ctwa_location="Whitefield").
"""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from workflow.state import LeadState
from db import crud

log = logging.getLogger(__name__)

_CONFIG_RE   = re.compile(r"\b(\d[Bb][Hh][Kk]|[Vv]illa)\b")
_LOCATION_RE = re.compile(r"\bin\s+([A-Za-z][A-Za-z\s]{2,20})\b")


async def store_attribution(db: AsyncSession, state: LeadState, referral: dict) -> None:
    source_id = referral.get("source_id") or referral.get("ad_source_type", "unknown")
    headline  = referral.get("headline", "")

    ctwa_config   = _extract_config(headline)
    ctwa_location = _extract_location(headline)

    await crud.update_lead(db, state["lead_id"], {
        "ctwa_source_id": source_id,
        "ctwa_config":    ctwa_config,
        "ctwa_location":  ctwa_location,
    })

    state["ctwa_source_id"] = source_id
    if ctwa_config:
        state["ctwa_config"] = ctwa_config
    if ctwa_location:
        state["ctwa_location"] = ctwa_location

    log.info(
        "CTWA attribution: lead=%s source=%s config=%s location=%s",
        state["lead_id"], source_id, ctwa_config, ctwa_location,
    )


def _extract_config(headline: str) -> str | None:
    m = _CONFIG_RE.search(headline)
    return m.group(1).upper() if m else None


def _extract_location(headline: str) -> str | None:
    m = _LOCATION_RE.search(headline)
    return m.group(1).strip().title() if m else None
