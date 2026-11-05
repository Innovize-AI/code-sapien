"""
Meta WhatsApp Cloud API — send text, document, and template messages.

Uses httpx async client. HMAC-SHA256 signature validation for webhooks
is handled in routes/webhook.py (not here).

Template variable convention:
  body_vars   — list of strings mapped to {{1}}, {{2}}, … in the body component
  header_vars — list of strings mapped to {{1}}, … in the header component (optional)

All send functions return the wamid (wa_message_id) string, or None on failure,
so callers can store it for delivery-status tracking.
"""

import logging

import httpx

from config import settings

log = logging.getLogger(__name__)

_BASE = settings.meta_graph_url


def _headers(access_token: str | None = None) -> dict:
    token = access_token or settings.meta_access_token
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _phone_number_id(wa_phone_number_id: str | None = None) -> str:
    return wa_phone_number_id or settings.meta_phone_number_id


def _to(phone: str) -> str:
    """Where a message really goes.

    Outside production, every send is redirected to TEST_FORWARD_NUMBER when it is set, so a staging
    deploy (scheduled follow-ups and broadcasts included) can never message a real buyer.
    """
    if not settings.is_production and settings.test_forward_number:
        return "+" + settings.test_forward_number.lstrip("+")
    return phone


async def send_text(
    phone: str,
    text: str,
    access_token: str | None = None,
    wa_phone_number_id: str | None = None,
) -> str | None:
    pid = _phone_number_id(wa_phone_number_id)
    log.info("WhatsApp send_text -> to=%r phone_number_id=%r text=%r", phone, pid, text[:80])
    url = f"{_BASE}/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _to(phone),
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=_headers(access_token))
        if resp.status_code != 200:
            log.error("WhatsApp send_text failed %s — %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return _extract_wamid(resp.json())


async def send_document(
    phone: str,
    doc_url: str,
    caption: str = "",
    access_token: str | None = None,
    wa_phone_number_id: str | None = None,
) -> str | None:
    pid = _phone_number_id(wa_phone_number_id)
    # WhatsApp document captions are capped at 1024 chars
    if len(caption) > 1024:
        caption = caption[:1021] + "..."
    url = f"{_BASE}/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _to(phone),
        "type": "document",
        "document": {"link": doc_url, "caption": caption},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=_headers(access_token))
        if resp.status_code != 200:
            log.error("WhatsApp send_document failed %s — %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return _extract_wamid(resp.json())


async def send_template(
    phone: str,
    template_name: str,
    body_vars: list[str] | None = None,
    header_vars: list[str] | None = None,
    language: str = "en",
    access_token: str | None = None,
    wa_phone_number_id: str | None = None,
) -> str | None:
    """
    Send a Meta-approved WhatsApp template message.

    body_vars   — positional substitutions for {{1}}, {{2}}, … in the body
    header_vars — positional substitutions for {{1}}, … in the header (rare)
    Returns the wamid so callers can track delivery status.
    """
    components: list[dict] = []

    if header_vars:
        components.append({
            "type": "header",
            "parameters": [{"type": "text", "text": v} for v in header_vars],
        })

    if body_vars:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": v} for v in body_vars],
        })

    payload: dict = {
        "messaging_product": "whatsapp",
        "to": _to(phone),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
        },
    }
    if components:
        payload["template"]["components"] = components

    pid = _phone_number_id(wa_phone_number_id)
    log.info(
        "WhatsApp send_template -> to=%r template=%r vars=%r",
        phone, template_name, body_vars,
    )
    url = f"{_BASE}/{pid}/messages"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=_headers(access_token))
        if resp.status_code != 200:
            log.error(
                "WhatsApp send_template failed %s — template=%r resp=%s",
                resp.status_code, template_name, resp.text,
            )
        resp.raise_for_status()
        return _extract_wamid(resp.json())


def _extract_wamid(body: dict) -> str | None:
    """Pull the wamid from a successful send response."""
    try:
        return body["messages"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return None


async def mark_read(
    wa_message_id: str,
    access_token: str | None = None,
    wa_phone_number_id: str | None = None,
) -> None:
    """Mark an inbound message as read (shows double blue tick to parent)."""
    url = f"{_BASE}/{_phone_number_id(wa_phone_number_id)}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wa_message_id,
    }
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(url, json=payload, headers=_headers(access_token))


async def fetch_media_url(media_id: str, access_token: str | None = None) -> str:
    """Resolve a Meta media ID to a downloadable URL (valid for ~5 min)."""
    url = f"{_BASE}/{media_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers(access_token))
        resp.raise_for_status()
        return resp.json()["url"]
