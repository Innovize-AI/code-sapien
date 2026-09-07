import os
import logging
import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL      = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_REVIEW_CHANNEL   = os.getenv("SLACK_REVIEW_CHANNEL", "#rfq-review")
COMPANY_NAME           = os.getenv("COMPANY_NAME", "Our Company")

_URGENCY_EMOJI = {
    "critical": "🔴",
    "rush":     "🟡",
    "standard": "🟢",
}


def notify_review_required(
    rfq_id: str,
    sender: str,
    buyer_name: str,
    review_notes: str,
    total: float,
    urgency: str,
    line_item_count: int,
    category: str,
) -> bool:
    """
    Post a review-required alert to the Slack channel.
    Returns True on success, False on failure.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("[SLACK] SLACK_WEBHOOK_URL not configured — skipping notification")
        return False

    urgency_emoji = _URGENCY_EMOJI.get(urgency, "⚪")
    ref = rfq_id[:8].upper()

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"⚠️  RFQ Needs Review — {ref}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*From*\n{buyer_name or sender}"},
                {"type": "mrkdwn", "text": f"*Contact*\n{sender}"},
                {"type": "mrkdwn", "text": f"*Urgency*\n{urgency_emoji} {urgency.capitalize()}"},
                {"type": "mrkdwn", "text": f"*Category*\n{(category or 'unknown').replace('_', ' ').title()}"},
                {"type": "mrkdwn", "text": f"*Line Items*\n{line_item_count}"},
                {"type": "mrkdwn", "text": f"*Est. Total*\n₹{total:,.2f}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Reason flagged:*\n{review_notes}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"RFQ ID: `{rfq_id}` · {COMPANY_NAME} RFQ Agent",
                }
            ],
        },
    ]

    payload = {
        "text": f"⚠️ RFQ {ref} needs review — {review_notes}",  # fallback for notifications
        "blocks": blocks,
    }

    if SLACK_REVIEW_CHANNEL:
        payload["channel"] = SLACK_REVIEW_CHANNEL

    try:
        response = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"[SLACK] Review alert posted for RFQ {rfq_id}")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"[SLACK] Webhook returned {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"[SLACK] Notification failed for RFQ {rfq_id}: {e}")

    return False


def notify_dispatched(rfq_id: str, sender: str, buyer_name: str, total: float, source: str) -> bool:
    """
    Post a success notification when a quotation is auto-dispatched.
    Useful for visibility even on happy-path RFQs.
    """
    if not SLACK_WEBHOOK_URL:
        return False

    ref = rfq_id[:8].upper()

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"✅ *Quotation Auto-Dispatched* — `{ref}`\n"
                    f"Sent to *{buyer_name or sender}* via *{source}*\n"
                    f"Total: *₹{total:,.2f}*"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"RFQ ID: `{rfq_id}` · {COMPANY_NAME} RFQ Agent"}
            ],
        },
    ]

    payload = {
        "text": f"✅ Quotation dispatched for RFQ {ref} — ₹{total:,.2f}",
        "blocks": blocks,
    }

    if SLACK_REVIEW_CHANNEL:
        payload["channel"] = SLACK_REVIEW_CHANNEL

    try:
        response = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"[SLACK] Dispatch notification posted for RFQ {rfq_id}")
        return True
    except Exception as e:
        logger.error(f"[SLACK] Dispatch notification failed for RFQ {rfq_id}: {e}")

    return False
