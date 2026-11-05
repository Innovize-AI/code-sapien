"""
Console API — staff actions (pause AI, send manual reply, broadcast, visit outcomes).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from db import crud
from db.schemas import ConversationLogOut, RetrievalLogOut
from services import whatsapp
from services import followup_sequences as fseq
from services import auth
from routes.guard import deny_agents, ensure_lead_access, guard

log = logging.getLogger(__name__)
router = APIRouter(prefix="/console", tags=["console"], dependencies=[Depends(guard)])


class PauseRequest(BaseModel):
    lead_id: str
    paused: bool


class ManualReplyRequest(BaseModel):
    lead_id: str
    session_id: str
    phone: str
    message_text: str
    admin_name: str | None = None


class BroadcastRequest(BaseModel):
    campaign_id: str
    phone_numbers: list[str]
    message_text: str


@router.post("/pause")
async def toggle_ai_pause(req: PauseRequest, actor: auth.Actor | None = Depends(guard),
                          db: AsyncSession = Depends(get_db)):
    await ensure_lead_access(db, actor, UUID(req.lead_id))
    await crud.update_lead(db, UUID(req.lead_id), {"ai_paused": req.paused})
    action = "paused" if req.paused else "resumed"
    log.info("AI %s for lead=%s", action, req.lead_id)
    return {"status": action, "lead_id": req.lead_id}


@router.post("/reply")
async def admin_reply(req: ManualReplyRequest, actor: auth.Actor | None = Depends(guard),
                      db: AsyncSession = Depends(get_db)):
    """
    Send a manual message from a staff member to a parent.
    Logs as sender_type='admin' so the frontend can render it differently.
    AI must be paused first (ai_paused=True) before using this.
    """
    from services import numbers as numbers_svc
    await ensure_lead_access(db, actor, UUID(req.lead_id))
    lead = await crud.get_lead(db, UUID(req.lead_id))
    firm = await crud.get_firm(db, lead.firm_id) if lead else None
    if lead is None or firm is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Lead not found")
    # Send from the number the buyer is talking to: the person's number if there is one
    number = await numbers_svc.number_for_lead(db, lead.number_id)
    token, wa_id = numbers_svc.credentials(firm, number)
    to = req.phone
    if not settings.is_production and settings.test_forward_number:
        to = "+" + settings.test_forward_number.lstrip("+")   # staging safety, as in the pipeline
    await whatsapp.send_text(to, req.message_text, access_token=token, wa_phone_number_id=wa_id)

    await crud.log_message(
        db,
        session_id=UUID(req.session_id),
        lead_id=UUID(req.lead_id),
        firm_id=lead.firm_id,
        direction="outbound",
        sender_type="admin",
        message_text=req.message_text,
        path_taken="admin_manual",
        number_id=lead.number_id,
    )

    log.info("Admin reply sent: lead=%s admin=%s", req.lead_id, req.admin_name or "unknown")
    return {"status": "sent"}


@router.post("/broadcast", dependencies=[Depends(deny_agents)])
async def send_broadcast(req: BroadcastRequest):
    sent, failed = 0, 0
    for phone in req.phone_numbers:
        try:
            await whatsapp.send_text(phone, req.message_text)
            sent += 1
        except Exception as exc:
            log.warning("Broadcast failed for %s: %s", phone, exc)
            failed += 1
    return {"sent": sent, "failed": failed, "campaign_id": req.campaign_id}


class NoShowRequest(BaseModel):
    lead_id: str


class AttendedRequest(BaseModel):
    lead_id: str
    outcome: str | None = None   # e.g. "booked_unit", "needs_followup", "not_interested"


async def _require_visit(db: AsyncSession, lead_id: UUID) -> None:
    """These actions are keyed by LEAD id. An id with no visit used to answer success and change
    nothing, which hid a client bug, so it is now a 404."""
    from fastapi import HTTPException
    from sqlalchemy import select
    from db.models import Visit
    found = (await db.execute(select(Visit.id).where(Visit.lead_id == lead_id).limit(1))).first()
    if not found:
        raise HTTPException(404, "No visit found for this lead")


@router.post("/visit/no-show")
async def mark_no_show(req: NoShowRequest, actor: auth.Actor | None = Depends(guard),
                       db: AsyncSession = Depends(get_db)):
    """
    Staff marks a visit as no-show.
    - Updates visit status → no_show
    - Resets lead_status → active (so AI re-engages if they message)
    - Cancels pending visit_reminder followups
    - Schedules Recovery Messages 1, 2, 3
    """
    lead_id = UUID(req.lead_id)
    await ensure_lead_access(db, actor, lead_id)
    await _require_visit(db, lead_id)

    await crud.mark_visit_no_show(db, lead_id)
    await crud.cancel_followups(db, lead_id, sequence="visit_reminder")

    lead = await crud.get_lead(db, lead_id)
    await fseq.schedule_no_show_recovery(
        db,
        lead_id=lead_id,
        lead_name=lead.lead_name if lead else None,
        booking_link=settings.booking_link,
        firm_id=lead.firm_id if lead else None,
    )

    log.info("No-show marked + recovery scheduled for lead=%s", lead_id)
    return {"status": "no_show_recovery_scheduled", "lead_id": req.lead_id}


@router.post("/visit/attended")
async def mark_attended(req: AttendedRequest, actor: auth.Actor | None = Depends(guard),
                        db: AsyncSession = Depends(get_db)):
    """
    Staff marks a visit as attended.
    - Updates visit status → completed, attended=True
    - Sets lead_status → converted
    - Cancels all pending followups (no more automated messages)
    """
    lead_id = UUID(req.lead_id)
    await ensure_lead_access(db, actor, lead_id)
    await _require_visit(db, lead_id)

    await crud.mark_visit_attended(db, lead_id, outcome=req.outcome)
    await crud.cancel_followups(db, lead_id)   # cancel everything — lead is converted

    log.info("Visit attended for lead=%s outcome=%s", lead_id, req.outcome)
    return {"status": "attended", "lead_id": req.lead_id, "outcome": req.outcome}


@router.get("/lead/{lead_id}/history", response_model=list[ConversationLogOut])
async def get_lead_history(lead_id: str, actor: auth.Actor | None = Depends(guard),
                           db: AsyncSession = Depends(get_db)):
    await ensure_lead_access(db, actor, UUID(lead_id))
    logs = await crud.get_lead_conversation(db, UUID(lead_id))

    # Attach the details of any brochure or video that went out with a reply
    from sqlalchemy import select
    from db.models import Resource
    ids = {l.resource_sent for l in logs if l.resource_sent}
    found = {}
    if ids:
        rows = (await db.execute(select(Resource).where(Resource.id.in_(ids)))).scalars()
        found = {r.id: {"id": r.id, "title": r.title, "type": r.resource_type or "pdf",
                        "url": r.url or None} for r in rows}
    out = []
    for l in logs:
        item = ConversationLogOut.model_validate(l)
        if l.resource_sent:
            # a resource removed since keeps its id so the attachment is still visible
            item.resource = found.get(l.resource_sent) or {
                "id": l.resource_sent, "title": l.resource_sent, "type": "pdf", "url": None}
        out.append(item)
    return out


@router.get("/lead/{lead_id}/summary")
async def lead_summary(lead_id: UUID, refresh: bool = False, actor: auth.Actor | None = Depends(guard),
                       db: AsyncSession = Depends(get_db)):
    """AI handover summary of the conversation. Cached until new messages arrive."""
    from fastapi import HTTPException
    from services import lead_summary as summaries
    await ensure_lead_access(db, actor, lead_id)
    try:
        return await summaries.get_summary(db, lead_id, refresh=refresh)
    except LookupError:
        raise HTTPException(404, "Lead not found")
    except Exception as exc:
        log.warning("summary failed for lead=%s: %s", lead_id, exc)
        raise HTTPException(502, "Summary is unavailable right now")


@router.get("/lead/{lead_id}/retrieval", response_model=list[RetrievalLogOut])
async def get_lead_retrieval(lead_id: str, actor: auth.Actor | None = Depends(guard),
                            db: AsyncSession = Depends(get_db)):
    await ensure_lead_access(db, actor, UUID(lead_id))
    logs = await crud.get_lead_retrieval_logs(db, UUID(lead_id))
    return logs
