"""
Meta WhatsApp webhook — verify + receive messages.

Security: HMAC-SHA256 signature validation on every POST.
Messages are processed async (background task) so Meta gets 200 < 20s.

Multi-tenant: verify token is checked against all active firms (any match passes).
"""

import asyncio
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from db import crud
from workflow.pipeline import process_message

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Meta webhook verification handshake — accepts any active firm's verify token."""
    params = request.query_params
    mode  = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode != "subscribe":
        raise HTTPException(status_code=403, detail="Verification failed")

    # Build set of valid tokens: all active firms + global settings fallback
    firms = await crud.list_firms(db)
    valid_tokens = {f.meta_webhook_verify_token for f in firms if f.meta_webhook_verify_token}
    if settings.meta_webhook_verify_token:
        valid_tokens.add(settings.meta_webhook_verify_token)

    if token in valid_tokens:
        log.info("Webhook verified successfully — token matched")
        return PlainTextResponse(challenge)

    log.warning("Webhook verification failed — mode=%r token=%r", mode, token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Receive inbound WhatsApp messages from Meta."""
    body = await request.body()

    _verify_signature(request, body)

    payload = json.loads(body)
    log.info("Meta webhook payload:\n%s", json.dumps(payload, indent=2))

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            metadata = value.get("metadata", {})

            for msg in messages:
                log.info(
                    "Inbound message — from=%s type=%s id=%s text=%r",
                    msg.get("from"),
                    msg.get("type"),
                    msg.get("id"),
                    msg.get("text", {}).get("body", ""),
                )
                background_tasks.add_task(process_message, msg, metadata)

    return {"status": "ok"}


def _verify_signature(request: Request, body: bytes) -> None:
    # Use global app secret as the HMAC key (firm-level secret lookup would require async)
    if not settings.meta_app_secret:
        # Without the app secret a request cannot be proven to come from Meta, so anyone could post
        # fake messages. Production refuses; other environments allow it for local testing.
        if settings.is_production:
            raise HTTPException(status_code=503, detail="Webhook signature secret is not configured")
        return

    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if not sig_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing signature")

    expected = hmac.new(
        settings.meta_app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig_header[7:], expected):
        raise HTTPException(status_code=401, detail="Invalid signature")
