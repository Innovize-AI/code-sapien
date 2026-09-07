"""
Email watcher — polls Gmail via IMAP for new unseen messages and auto-processes RFQs.
Behaviour mirrors n8n's "Email Trigger (IMAP)" node: check every N seconds,
grab unseen messages, run the RFQ pipeline for any that look like an RFQ.
"""
import asyncio
import logging
import os
import uuid
import io
import imaplib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# How often to check for new mail (seconds). Override with EMAIL_POLL_INTERVAL env var.
_DEFAULT_POLL_INTERVAL = 60

_running = False

# IDs already evaluated this session — prevents re-logging non-RFQ emails every poll
_seen_ids: set[bytes] = set()

# Only process emails received after this timestamp (set at startup)
_start_time: datetime = datetime.now(timezone.utc)


async def start_watcher():
    """Start the background email polling loop. Call once on app startup."""
    global _running
    if _running:
        return
    _running = True
    interval = int(os.getenv("EMAIL_POLL_INTERVAL", _DEFAULT_POLL_INTERVAL))
    logger.info(f"[EMAIL WATCHER] Starting — polling every {interval}s")
    asyncio.create_task(_poll_loop(interval))


async def _poll_loop(interval: int):
    # Wait a few seconds after startup so the DB is warm before first check
    await asyncio.sleep(10)
    while True:
        loop = asyncio.get_running_loop()
        try:
            await _check_connected_accounts(loop)
        except Exception as exc:
            logger.error(f"[EMAIL WATCHER] Poll error: {exc}")
        await asyncio.sleep(interval)


def _check_new_emails(loop: asyncio.AbstractEventLoop):
    """Synchronous: fetch unseen messages and submit RFQs. Runs in a thread."""
    from services.gmail_inbox import _lock, _get_conn, _reset_conn

    with _lock:
        try:
            imap = _get_conn()
            imap.select("INBOX")
            since_date = _start_time.strftime("%d-%b-%Y")
            _, data = imap.search(None, "UNSEEN", "SINCE", since_date)
            ids = data[0].split()

            new_ids = [eid for eid in ids if eid not in _seen_ids]
            if not new_ids:
                return

            logger.info(f"[EMAIL WATCHER] {len(new_ids)} new unseen email(s) to evaluate")

            for eid in new_ids:
                _seen_ids.add(eid)
                try:
                    _process_one(imap, eid, loop)
                except Exception as exc:
                    logger.error(f"[EMAIL WATCHER] Failed to process email {eid}: {exc}")

        except Exception as exc:
            logger.error(f"[EMAIL WATCHER] IMAP error: {exc}")
            _reset_conn()


def _process_one(imap: imaplib.IMAP4_SSL, eid: bytes, loop: asyncio.AbstractEventLoop):
    """Parse a single email and, if it's an RFQ, kick off the pipeline."""
    from services.gmail_inbox import _decode_header, _get_body, _get_attachments, _tag_email

    import re
    _, msg_data = imap.fetch(eid, "(RFC822 X-GM-THRID X-GM-MSGID)")
    meta_line = msg_data[0][0].decode()
    import email as _email
    import email.utils as _eu

    raw = msg_data[0][1]
    msg = _email.message_from_bytes(raw)

    thread_match = re.search(r"X-GM-THRID (\d+)", meta_line)
    thread_id = thread_match.group(1) if thread_match else None

    # Use Gmail REST-compatible hex message ID so DB email_id matches inbox links
    msgid_match = re.search(r"X-GM-MSGID (\d+)", meta_line)
    gmail_hex_id = hex(int(msgid_match.group(1)))[2:] if msgid_match else eid.decode()

    subject = _decode_header(msg.get("Subject", "(No Subject)"))
    from_raw = msg.get("From", "")
    name, addr = _eu.parseaddr(from_raw)

    body = _get_body(msg)
    tag = _tag_email(subject, body, msg=msg)

    if tag != "RFQ":
        # Leave the email unread — the watcher won't re-evaluate it this session
        # (tracked in _seen_ids) and the user still sees it as unread in their inbox.
        logger.debug(f"[EMAIL WATCHER] Skipping {eid.decode()} — tagged '{tag}' ('{subject[:50]}')")
        return

    logger.info(f"[EMAIL WATCHER] RFQ detected: '{subject}' from {addr}")
    # Mark as read only for emails we're about to process
    imap.store(eid, "+FLAGS", "\\Seen")

    # Submit to the RFQ pipeline asynchronously (schedule from this sync thread)
    rfq_id = str(uuid.uuid4())
    saved_excel_path = None

    # Extract attachment text
    attachment_texts = []
    for part in msg.walk():
        disp = str(part.get("Content-Disposition", ""))
        if "attachment" not in disp:
            continue
        filename = _decode_header(part.get_filename() or "")
        payload = part.get_payload(decode=True)
        if not payload or not filename:
            continue
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            if suffix == "pdf":
                import pdfplumber
                with pdfplumber.open(io.BytesIO(payload)) as pdf:
                    pages = []
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pages.append(t)
                    text = "\n".join(pages).strip()
                if len(text) < 100:
                    from services.vision_extractor import extract_from_bytes
                    text = extract_from_bytes(payload, "application/pdf")
                attachment_texts.append(f"[Attachment: {filename}]\n{text}")
            elif suffix in ("xlsx", "xlsm", "xls", "csv"):
                from services.excel_extractor import extract_excel_bytes
                text = extract_excel_bytes(payload, filename)
                attachment_texts.append(f"[Attachment: {filename}]\n{text}")
                try:
                    import os
                    storage_dir = os.path.join(os.getcwd(), "storage", "attachments")
                    os.makedirs(storage_dir, exist_ok=True)
                    saved_excel_path = os.path.join(storage_dir, f"{rfq_id}_{filename}")
                    with open(saved_excel_path, "wb") as f:
                        f.write(payload)
                    logger.info(f"[EMAIL WATCHER] Saved incoming pricing template to {saved_excel_path}")
                except Exception as storage_ex:
                    logger.warning(f"[EMAIL WATCHER] Could not save Excel attachment locally: {storage_ex}")
            elif suffix in ("docx", "doc"):
                import docx
                doc = docx.Document(io.BytesIO(payload))
                parts = [p.text for p in doc.paragraphs if p.text.strip()]
                attachment_texts.append(f"[Attachment: {filename}]\n" + "\n".join(parts))
            elif suffix == "txt":
                attachment_texts.append(f"[Attachment: {filename}]\n" + payload.decode("utf-8", errors="replace"))
        except Exception as ex:
            logger.warning(f"[EMAIL WATCHER] Could not extract {filename}: {ex}")

    combined_body = body or ""
    if attachment_texts:
        combined_body = combined_body + "\n\n" + "\n\n".join(attachment_texts)

    if not combined_body.strip():
        logger.warning(f"[EMAIL WATCHER] Email {eid.decode()} has no extractable text — skipping")
        return

    asyncio.run_coroutine_threadsafe(_run_pipeline(rfq_id, combined_body, subject, addr, gmail_hex_id, thread_id, saved_excel_path), loop)
    logger.info(f"[EMAIL WATCHER] Submitted rfq_id={rfq_id} for '{subject}'")


async def _check_connected_accounts(loop: asyncio.AbstractEventLoop):
    """Poll UNSEEN emails for every active OAuth-connected account via IMAP XOAUTH2."""
    from db.database import SessionLocal
    from db.models import ConnectedAccount
    from sqlalchemy import select
    from services.gmail_oauth import credentials_from_token_json

    async with SessionLocal() as db:
        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.active == True)
        )
        accounts = result.scalars().all()

    if not accounts:
        logger.debug("[EMAIL WATCHER] No connected accounts to poll")
        return

    for account in accounts:
        try:
            creds = credentials_from_token_json(account.token_json)
            if not creds:
                logger.warning(f"[EMAIL WATCHER] Invalid/expired token for {account.email} — skipping")
                continue
            token_preview = (creds.token or "")[:20]
            logger.info(f"[EMAIL WATCHER] Using token for {account.email}: {token_preview}... valid={creds.valid} expired={creds.expired} scopes={creds.scopes}")
            await asyncio.to_thread(_check_account_imap, account.email, creds.token, loop)
        except Exception as exc:
            logger.error(f"[EMAIL WATCHER] Poll failed for {account.email}: {exc}")


def _check_account_imap(email: str, access_token: str, loop: asyncio.AbstractEventLoop):
    """IMAP XOAUTH2 check for a connected OAuth account."""
    import imaplib

    auth_bytes = f"user={email}\x01auth=Bearer {access_token}\x01\x01".encode()

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.authenticate("XOAUTH2", lambda x: auth_bytes)
        imap.select("INBOX")

        # Only fetch UNSEEN emails received since watcher started — avoids processing backlog
        since_date = _start_time.strftime("%d-%b-%Y")
        _, data = imap.search(None, "UNSEEN", "SINCE", since_date)
        ids = data[0].split()
        new_ids = [eid for eid in ids if eid not in _seen_ids]

        if not new_ids:
            imap.logout()
            return

        logger.info(f"[EMAIL WATCHER] {len(new_ids)} new email(s) for {email}")
        for eid in new_ids:
            _seen_ids.add(eid)
            try:
                _process_one(imap, eid, loop)
            except Exception as exc:
                logger.error(f"[EMAIL WATCHER] Failed to process email {eid} for {email}: {exc}")

        imap.logout()
    except Exception as exc:
        logger.error(f"[EMAIL WATCHER] IMAP XOAUTH2 failed for {email}: {exc}")


async def _run_pipeline(rfq_id: str, raw_text: str, subject: str, sender: str, email_id: str, thread_id: str, attachment_path: str = None):
    from db.database import SessionLocal
    from db.crud import save_rfq
    from workflow.graph import graph

    try:
        config = {"configurable": {"thread_id": rfq_id}}
        initial_state = {
            "rfq_id": rfq_id,
            "raw_content": raw_text,
            "subject": subject,
            "sender": sender,
            "source": "email",
            "email_id": email_id,
            "thread_id": thread_id,
            "attachment_path": attachment_path,
        }
        result = await graph.ainvoke(initial_state, config=config)
        async with SessionLocal() as db:
            await save_rfq(db, result, result.get("status", "quoted"))
        logger.info(f"[EMAIL WATCHER] Pipeline complete for rfq_id={rfq_id} status={result.get('status')}")
    except Exception as exc:
        logger.error(f"[EMAIL WATCHER] Pipeline failed for rfq_id={rfq_id}: {exc}", exc_info=True)
