"""
Scheduler service — APScheduler AsyncIOScheduler.

Uses the DB (followup_schedules table) as the job store, so pending follow-ups
survive process restarts. Every 60 seconds the dispatcher polls for due rows,
sends the WhatsApp template, and marks each row as sent (or leaves it pending
on failure so it retries the next cycle).

Variable convention for body_vars:
  Store followup.variables as a JSON list of strings in the order the
  Meta template expects them, e.g. ["Rahul", "Saturday 9th", "11 AM"].
  Legacy dict format ({"name": "Rahul", ...}) is also handled — values are
  extracted in insertion order (Python 3.7+).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.database import SessionLocal
from db import crud
from services import whatsapp

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _dispatch_pending_followups,
        trigger="interval",
        seconds=60,
        id="followup_dispatch",
        max_instances=1,   # prevent overlap if a dispatch cycle takes > 60s
        coalesce=True,     # skip missed fires, run once when back online
    )
    _scheduler.start()
    log.info("APScheduler started — followup dispatch every 60s")


def stop() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("APScheduler stopped")


async def _dispatch_pending_followups() -> None:
    async with SessionLocal() as db:
        rows = await crud.get_pending_followups_with_phones(db)
        if not rows:
            return

        log.info("Followup dispatch: %d job(s) due", len(rows))

        for followup, phone, access_token, wa_phone_number_id in rows:
            try:
                body_vars = _resolve_vars(followup.variables)
                wamid = await whatsapp.send_template(
                    phone=phone,
                    template_name=followup.template_name,
                    body_vars=body_vars,
                    access_token=access_token,
                    wa_phone_number_id=wa_phone_number_id,
                )
                await crud.mark_followup_sent(db, followup.id)
                log.info(
                    "Followup sent: template=%s lead=%s wamid=%s",
                    followup.template_name, followup.lead_id, wamid,
                )
            except Exception as exc:
                # Leave status=pending — will retry on next 60s cycle
                log.error(
                    "Followup dispatch failed: template=%s lead=%s error=%s",
                    followup.template_name, followup.lead_id, exc,
                )


def _resolve_vars(variables) -> list[str] | None:
    """Normalise stored variables to a flat list of strings for send_template."""
    if not variables:
        return None
    if isinstance(variables, list):
        return [str(v) for v in variables]
    if isinstance(variables, dict):
        # Dict stored in insertion order — extract values
        return [str(v) for v in variables.values()]
    return None
