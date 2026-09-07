import asyncio
import logging
import os
import httpx
from workflow.state import RFQState
from services.email_service import send_quotation_email, send_review_alert_email
from services.slack_service import notify_review_required, notify_dispatched

logger = logging.getLogger(__name__)


def dispatch_node(state: RFQState) -> dict:
    """Auto-approved: send quotation to buyer."""
    logger.info(f"[DISPATCH] RFQ {state['rfq_id']} — auto-approved, dispatching to {state['sender']}")

    source = state.get("source")
    if source == "email" or source == "upload":
        success = send_quotation_email(
            to=state["sender"],
            rfq_id=state["rfq_id"],
            buyer_name=state.get("buyer_name") or "Valued Customer",
            draft_quote=state.get("draft_quote") or "",
            total=state.get("total") or 0.0,
        )
        if not success:
            logger.warning(f"[DISPATCH] Email failed for RFQ {state['rfq_id']} — routing to human queue")
            return _fallback_to_queue(state, "email delivery failed")

    elif source == "whatsapp":
        asyncio.create_task(_send_whatsapp_quote(state))

    notify_dispatched(
        rfq_id=state["rfq_id"],
        sender=state.get("sender", ""),
        buyer_name=state.get("buyer_name") or "",
        total=state.get("total") or 0.0,
        source=source or "unknown",
    )

    return {"status": "dispatched"}


def human_queue_node(state: RFQState) -> dict:
    """Needs review: flag and notify reviewer."""
    reasons = []
    if state.get("complexity") == "review":
        reasons.append("complex requirements")
    if (state.get("pricing_confidence") or 1.0) < 0.75:
        reasons.append(f"low pricing confidence ({state.get('pricing_confidence')})")
    if state.get("unfulfillable_items"):
        reasons.append(f"{len(state['unfulfillable_items'])} unfulfillable items")
    if state.get("error"):
        reasons.append(f"error: {state['error']}")

    review_notes = "Flagged for review: " + ", ".join(reasons) if reasons else "Manual review required"
    logger.info(f"[QUEUE] RFQ {state['rfq_id']} — {review_notes}")

    send_review_alert_email(
        rfq_id=state["rfq_id"],
        sender=state.get("sender", "unknown"),
        review_notes=review_notes,
        total=state.get("total") or 0.0,
    )

    notify_review_required(
        rfq_id=state["rfq_id"],
        sender=state.get("sender", "unknown"),
        buyer_name=state.get("buyer_name") or "",
        review_notes=review_notes,
        total=state.get("total") or 0.0,
        urgency=state.get("urgency") or "standard",
        line_item_count=len(state.get("line_items") or []),
        category=state.get("category") or "unknown",
    )

    return {"status": "pending_review", "review_notes": review_notes}


def _fallback_to_queue(state: RFQState, reason: str) -> dict:
    review_notes = f"Auto-dispatch failed: {reason} — manual send required"
    send_review_alert_email(
        rfq_id=state["rfq_id"],
        sender=state.get("sender", "unknown"),
        review_notes=review_notes,
        total=state.get("total") or 0.0,
    )
    notify_review_required(
        rfq_id=state["rfq_id"],
        sender=state.get("sender", "unknown"),
        buyer_name=state.get("buyer_name") or "",
        review_notes=review_notes,
        total=state.get("total") or 0.0,
        urgency=state.get("urgency") or "standard",
        line_item_count=len(state.get("line_items") or []),
        category=state.get("category") or "unknown",
    )
    return {"status": "pending_review", "review_notes": review_notes}


async def _send_whatsapp_quote(state: RFQState):
    message = (
        f"Hi {state.get('buyer_name', 'there')}, here is your quotation summary:\n\n"
        f"{(state.get('draft_quote') or '')[:1000]}\n\n"
        f"Total: ₹{state.get('total', 0):,.2f}\n"
        "Our team will follow up with the full PDF shortly."
    )
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_number_id:
        logger.warning("[DISPATCH] WhatsApp credentials not configured")
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": state["sender"],
                "type": "text",
                "text": {"body": message},
            },
        )
