"""
Follow-up sequence definitions and scheduling helpers.

Sequences
---------
pre_qualification  — triggered after the first agent reply; re-triggered on every
                     re-engagement so the D3/D7 clock resets from the latest reply.
                     Cancelled when the lead advances past portfolio_match.

pre_visit          — triggered when the lead advances to consideration or booking
                     (qualified but hasn't confirmed a visit date yet).
                     Cancelled when a visit date is captured.

visit_reminder     — scheduled immediately when a visit is booked (separate step).
no_show_recovery   — scheduled externally via the console when staff marks no-show.

Template variable convention
----------------------------
Variables are stored in followup_schedules.variables as a JSON list of strings,
matching the positional {{1}} {{2}} … placeholders in the Meta-approved template.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time as dtime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db import crud

# IST is UTC+5:30 — visit times from leads are in local time
_IST_OFFSET = timedelta(hours=5, minutes=30)

log = logging.getLogger(__name__)

# ── Template name registry ────────────────────────────────────────────────────
# Maps (stage_bucket, day) → Meta template name.
# stage_bucket groups portfolio_match with qualification (same content).

_PRE_QUAL_TEMPLATES: dict[tuple[str, int], str] = {
    ("discovery",         3): "stl_silent_greeting_d3",
    ("discovery",         7): "stl_silent_greeting_d7",
    ("qualification",     3): "stl_silent_qual_d3",
    ("qualification",     7): "stl_silent_qual_d7",
    ("portfolio_match",   3): "stl_silent_qual_d3",
    ("portfolio_match",   7): "stl_silent_qual_d7",
}

_PRE_VISIT_TEMPLATES: dict[tuple[str, int], str] = {
    ("consideration",     3): "stl_silent_booking_d3",
    ("consideration",     7): "stl_silent_booking_d7",
    ("booking",           3): "stl_silent_booking_d3",
    ("booking",           7): "stl_silent_booking_d7",
}

_NO_SHOW_TEMPLATES: dict[int, str] = {
    1: "stl_recovery_1",
    2: "stl_recovery_2",
    3: "stl_recovery_3",
}

# Days after which recovery messages fire
_NO_SHOW_DELAYS = {1: 1, 2: 2, 3: 4}   # day 1 → +1d, day 2 → +2d, day 3 → +4d


# ── Pre-qualification sequence ────────────────────────────────────────────────

async def schedule_pre_qualification(
    db: AsyncSession,
    lead_id: UUID,
    stage: str,
    lead_name: str | None,
    config: str | None,
    firm_id=None,
) -> None:
    """
    Schedule D3 and D7 silent-lead follow-ups based on current stage.
    Always cancels existing pre_qualification entries first so the clock resets
    from the most recent engagement.
    """
    await crud.cancel_followups(db, lead_id, sequence="pre_qualification")

    name_var  = lead_name or "there"
    config_var = config or "your flat"
    now = datetime.now(timezone.utc)

    for day in (3, 7):
        template = _PRE_QUAL_TEMPLATES.get((stage, day))
        if not template:
            continue

        if stage in ("qualification", "portfolio_match") and day == 3:
            body_vars = [name_var, config_var]
        else:
            body_vars = [name_var]

        await crud.schedule_followup(
            db,
            lead_id=lead_id,
            sequence="pre_qualification",
            day=day,
            template_name=template,
            variables=body_vars,
            scheduled_at=now + timedelta(days=day),
            firm_id=firm_id,
        )

    log.info(
        "Scheduled pre_qualification D3+D7 for lead=%s stage=%s",
        lead_id, stage,
    )


# ── Pre-visit sequence ────────────────────────────────────────────────────────

async def schedule_pre_visit(
    db: AsyncSession,
    lead_id: UUID,
    stage: str,
    lead_name: str | None,
    firm_id=None,
) -> None:
    """
    Schedule D3 and D7 'qualified but silent at booking' follow-ups.
    Cancels existing pre_qualification entries (lead has advanced past qualification).
    """
    await crud.cancel_followups(db, lead_id, sequence="pre_qualification")
    await crud.cancel_followups(db, lead_id, sequence="pre_visit")

    name_var = lead_name or "there"
    now = datetime.now(timezone.utc)

    for day in (3, 7):
        template = _PRE_VISIT_TEMPLATES.get((stage, day))
        if not template:
            continue

        await crud.schedule_followup(
            db,
            lead_id=lead_id,
            sequence="pre_visit",
            day=day,
            template_name=template,
            variables=[name_var],
            scheduled_at=now + timedelta(days=day),
            firm_id=firm_id,
        )

    log.info(
        "Scheduled pre_visit D3+D7 for lead=%s stage=%s",
        lead_id, stage,
    )


# ── No-show recovery sequence ─────────────────────────────────────────────────

async def schedule_no_show_recovery(
    db: AsyncSession,
    lead_id: UUID,
    lead_name: str | None,
    booking_link: str = "[Booking Link]",
    firm_id=None,
) -> None:
    """
    Schedule Recovery Messages 1, 2, 3 after a no-show.
    Called from the console when staff marks a visit as no-show.
    """
    await crud.cancel_followups(db, lead_id, sequence="no_show_recovery")

    name_var = lead_name or "there"
    now = datetime.now(timezone.utc)

    for msg_num, delay_days in _NO_SHOW_DELAYS.items():
        template = _NO_SHOW_TEMPLATES[msg_num]

        if msg_num in (1, 3):
            body_vars = [name_var, booking_link]
        else:
            body_vars = [name_var]

        await crud.schedule_followup(
            db,
            lead_id=lead_id,
            sequence="no_show_recovery",
            day=msg_num,
            template_name=template,
            variables=body_vars,
            scheduled_at=now + timedelta(days=delay_days),
            firm_id=firm_id,
        )

    log.info("Scheduled no_show_recovery (3 messages) for lead=%s", lead_id)


# ── Visit reminder sequence ───────────────────────────────────────────────────

async def schedule_visit_reminders(
    db: AsyncSession,
    lead_id: UUID,
    lead_name: str | None,
    visit_date: date,
    visit_time_slot: str | None,
    lead_type: str | None,
    firm_id=None,
) -> None:
    """
    Schedule three visit reminder messages immediately after a visit is booked:
      1. Instant Confirmation  — fires within 60s (picked up by next scheduler tick)
      2. 24-Hour Reminder      — fires 24h before the visit datetime
      3. 2-Hour Alert          — fires 2h before the visit datetime

    Skips 24h/2h reminders if the computed fire time is already in the past
    (e.g. last-minute same-day booking).
    """
    from config import settings

    await crud.cancel_followups(db, lead_id, sequence="visit_reminder")

    name_var      = lead_name or "there"
    visit_dt_utc  = _visit_datetime_utc(visit_date, visit_time_slot)
    date_str      = _format_date(visit_date)
    time_str      = visit_time_slot or "time to be confirmed"
    maps_link     = (
        settings.maps_link_real_estate
        if lead_type == "real_estate"
        else settings.maps_link_interior
    )
    now = datetime.now(timezone.utc)

    # 1. Instant Confirmation — fires within 60s
    await crud.schedule_followup(
        db,
        lead_id=lead_id,
        sequence="visit_reminder",
        day=0,
        template_name="stl_visit_confirmation",
        variables=[name_var, date_str, time_str, maps_link],
        scheduled_at=now + timedelta(seconds=10),
        firm_id=firm_id,
    )

    # 2. 24-Hour Reminder
    reminder_24h_at = visit_dt_utc - timedelta(hours=24)
    if reminder_24h_at > now:
        await crud.schedule_followup(
            db,
            lead_id=lead_id,
            sequence="visit_reminder",
            day=1,
            template_name="stl_reminder_24h",
            variables=[name_var, time_str],
            scheduled_at=reminder_24h_at,
            firm_id=firm_id,
        )

    # 3. 2-Hour Alert
    reminder_2h_at = visit_dt_utc - timedelta(hours=2)
    if reminder_2h_at > now:
        await crud.schedule_followup(
            db,
            lead_id=lead_id,
            sequence="visit_reminder",
            day=2,
            template_name="stl_reminder_2h",
            variables=[name_var, maps_link],
            scheduled_at=reminder_2h_at,
            firm_id=firm_id,
        )

    log.info(
        "Scheduled visit_reminder sequence for lead=%s visit=%s %s",
        lead_id, visit_date, visit_time_slot or "(time TBC)",
    )


# ── Time helpers ──────────────────────────────────────────────────────────────

def _parse_time_slot(slot: str | None) -> dtime:
    """Parse a free-text time slot to a time object. Defaults to 11:00 if unparseable."""
    if not slot:
        return dtime(11, 0)

    s = slot.strip().lower()

    if "morning" in s:
        return dtime(10, 0)
    if "afternoon" in s:
        return dtime(14, 0)
    if "evening" in s:
        return dtime(17, 0)

    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if m:
        hour   = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm   = m.group(3)

        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return dtime(hour, minute)

    return dtime(11, 0)


def _visit_datetime_utc(visit_date: date, time_slot: str | None) -> datetime:
    """Combine visit_date + time_slot into a UTC datetime (IST → UTC conversion)."""
    local_time = _parse_time_slot(time_slot)
    local_dt   = datetime.combine(visit_date, local_time)
    # Treat as IST (UTC+5:30) and convert to UTC
    return local_dt.replace(tzinfo=timezone.utc) - _IST_OFFSET


def _format_date(d: date) -> str:
    """Format date as 'Saturday, 15th August' for template variables."""
    day = d.day
    suffix = (
        "th" if 11 <= day <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    )
    return d.strftime(f"%A, {day}{suffix} %B")


# ── Cancellation helpers ──────────────────────────────────────────────────────

async def cancel_engagement_followups(
    db: AsyncSession,
    lead_id: UUID,
    stage: str,
) -> None:
    """
    Cancel pre_qualification or pre_visit followups when a lead re-engages.
    Visit reminders and no_show_recovery are left untouched.
    """
    if stage in ("discovery", "qualification", "portfolio_match"):
        await crud.cancel_followups(db, lead_id, sequence="pre_qualification")
    elif stage in ("consideration", "booking", "conversion"):
        await crud.cancel_followups(db, lead_id, sequence="pre_visit")
