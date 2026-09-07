import base64
import json
import uuid
import asyncio
import logging
import os
import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Query

from workflow.state import RFQState
from workflow.graph import graph

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == os.getenv("WHATSAPP_VERIFY_TOKEN", "rfq_verify"):
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    payload = await request.json()

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        message = change["messages"][0]

        sender = message["from"]
        msg_type = message["type"]
        rfq_id = str(uuid.uuid4())

        raw_content = ""
        attachment_url = None

        if msg_type == "text":
            raw_content = message["text"]["body"]
        elif msg_type == "document":
            doc = message["document"]
            media_url = await _get_media_url(doc["id"])
            attachment_url = media_url
            raw_content = doc.get("caption", "")
            # Download and extract text from PDF/Excel attachments
            filename = doc.get("filename", "attachment")
            mime_type = doc.get("mime_type", "application/pdf")
            extracted = await _extract_whatsapp_media(media_url, filename, mime_type)
            if extracted:
                raw_content = (raw_content + "\n\n" + extracted).strip()
        elif msg_type == "image":
            img = message["image"]
            media_url = await _get_media_url(img["id"])
            attachment_url = media_url
            raw_content = img.get("caption", "")
            # Use Gemini Vision to read handwritten lists / photos
            extracted = await _extract_whatsapp_media(media_url, "image.jpg", "image/jpeg")
            if extracted:
                raw_content = (raw_content + "\n\n" + extracted).strip()

        initial_state: RFQState = {
            "rfq_id": rfq_id,
            "source": "whatsapp",
            "sender": sender,
            "raw_content": raw_content,
            "attachment_path": None,
            "attachment_url": attachment_url,
            "subject": None,
            "line_items": [],
            "missing_fields": [],
            "buyer_name": None,
            "buyer_contact": None,
            "delivery_location": None,
            "rfq_deadline": None,
            "urgency": "standard",
            "complexity": "auto",
            "category": None,
            "catalog_matches": [],
            "feasibility": [],
            "unfulfillable_items": [],
            "line_pricing": [],
            "subtotal": 0.0,
            "total": 0.0,
            "pricing_confidence": 0.0,
            "draft_quote": None,
            "pdf_path": None,
            "status": "processing",
            "review_notes": None,
            "error": None,
        }

        config = {"configurable": {"thread_id": rfq_id}}
        asyncio.create_task(graph.ainvoke(initial_state, config=config))

        await _send_whatsapp_message(sender, "Got your RFQ! Preparing your quotation, will respond shortly.")

    except (KeyError, IndexError):
        pass  # non-message events (delivery receipts, read receipts)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Gmail Pub/Sub push webhook
# ---------------------------------------------------------------------------

@router.post("/webhook/gmail")
async def gmail_pubsub_webhook(request: Request):
    """
    Receives Gmail push notifications via Google Cloud Pub/Sub.
    Google posts here whenever a new email arrives in the watched inbox.
    We just trigger the existing IMAP check — no duplicate pipeline logic.
    """
    # Optional: verify the Bearer token Google sends matches PUBSUB_VERIFY_TOKEN
    expected_token = os.getenv("PUBSUB_VERIFY_TOKEN", "")
    if expected_token:
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if token != expected_token:
            logger.warning("[GMAIL WEBHOOK] Invalid Pub/Sub token — rejecting")
            raise HTTPException(status_code=403, detail="Invalid token")

    email_addr = None
    try:
        body = await request.json()
        message = body.get("message", {})
        data_b64 = message.get("data", "")
        if data_b64:
            info = json.loads(base64.b64decode(data_b64).decode())
            history_id = info.get("historyId")
            email_addr = info.get("emailAddress")
            logger.info(f"[GMAIL WEBHOOK] Push received — historyId={history_id} account={email_addr}")
    except Exception as exc:
        logger.warning(f"[GMAIL WEBHOOK] Could not parse Pub/Sub payload: {exc}")

    loop = asyncio.get_running_loop()

    if email_addr:
        asyncio.create_task(_check_oauth_account(email_addr, loop))
    else:
        # No email in payload — check all connected accounts
        asyncio.create_task(_check_all_accounts(loop))

    # Always return 200 — Pub/Sub retries on non-2xx
    return {"status": "ok"}


async def _check_all_accounts(loop: asyncio.AbstractEventLoop):
    """Fallback: check all connected accounts when Pub/Sub payload has no emailAddress."""
    from services.email_watcher import _check_connected_accounts
    await _check_connected_accounts(loop)


async def _check_oauth_account(email: str, loop: asyncio.AbstractEventLoop):
    """Load OAuth token from DB and trigger IMAP check for a connected account."""
    try:
        from db.database import SessionLocal
        from db.models import ConnectedAccount
        from sqlalchemy import select
        from services.gmail_oauth import credentials_from_token_json
        from services.email_watcher import _check_account_imap

        async with SessionLocal() as db:
            result = await db.execute(
                select(ConnectedAccount).where(
                    ConnectedAccount.email == email,
                    ConnectedAccount.active == True,
                )
            )
            account = result.scalars().first()

        if not account:
            logger.warning(f"[GMAIL WEBHOOK] No active connected account found for {email}")
            return

        creds = credentials_from_token_json(account.token_json)
        if not creds:
            logger.warning(f"[GMAIL WEBHOOK] Could not load credentials for {email}")
            return

        await asyncio.to_thread(_check_account_imap, email, creds.token, loop)
    except Exception as exc:
        logger.error(f"[GMAIL WEBHOOK] OAuth account check failed for {email}: {exc}")


async def _extract_whatsapp_media(url: str, filename: str, mime_type: str) -> str:
    """Download WhatsApp media and extract text via appropriate extractor."""
    token = os.getenv("WHATSAPP_TOKEN", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            data = resp.content

        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if mime_type.startswith("image/") or suffix in ("jpg", "jpeg", "png", "webp", "gif"):
            from services.vision_extractor import extract_from_bytes
            return extract_from_bytes(data, mime_type)
        elif mime_type == "application/pdf" or suffix == "pdf":
            from services.vision_extractor import extract_from_bytes
            import pdfplumber, io
            # Try pdfplumber first, fall back to vision
            try:
                parts = []
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            parts.append(t)
                text = "\n".join(parts).strip()
                if len(text) >= 100:
                    return text
            except Exception:
                pass
            return extract_from_bytes(data, "application/pdf")
        elif suffix in ("xlsx", "xlsm", "xls", "csv"):
            from services.excel_extractor import extract_excel_bytes
            return extract_excel_bytes(data, filename)
    except Exception as e:
        logger.warning(f"[WHATSAPP] Media extraction failed for {filename}: {e}")
    return ""


async def _get_media_url(media_id: str) -> str:
    token = os.getenv("WHATSAPP_TOKEN", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json().get("url", "")


async def _send_whatsapp_message(to: str, text: str):
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_number_id:
        logger.warning("WhatsApp credentials not configured")
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )
