"""Gmail inbox reader via IMAP — persistent connection with auto-reconnect."""
import os
import imaplib
import email
import email.header
import email.message
import email.utils
import logging
import re
import threading
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

_wf_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_wf_env)

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# ── Persistent connection ────────────────────────────────────────────────────
# One SSL connection is kept alive for the process lifetime.
# A threading.Lock serialises all IMAP I/O (IMAP is single-stream).
# On any error the connection is discarded; the next caller reconnects.

_lock: threading.Lock = threading.Lock()
_conn: Optional[imaplib.IMAP4_SSL] = None


def _connect() -> imaplib.IMAP4_SSL:
    user = os.getenv("GMAIL_USER", "").strip().strip('"')
    password = os.getenv("GMAIL_PASSWORD", "").strip().strip('"')
    if not user or not password:
        raise RuntimeError("GMAIL_USER and GMAIL_PASSWORD must be set in .env")
    c = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    c.login(user, password)
    logger.info("[GMAIL] New IMAP connection established (app password)")
    return c


def _connect_oauth(email_addr: str, access_token: str) -> imaplib.IMAP4_SSL:
    """Open a fresh IMAP connection using XOAUTH2 for a connected account."""
    auth_bytes = f"user={email_addr}\x01auth=Bearer {access_token}\x01\x01".encode()
    c = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    c.authenticate("XOAUTH2", lambda x: auth_bytes)
    logger.info(f"[GMAIL] IMAP connection established via OAuth for {email_addr}")
    return c


def _get_conn() -> imaplib.IMAP4_SSL:
    """Return the live connection, reconnecting if needed. Caller must hold _lock."""
    global _conn
    if _conn is not None:
        try:
            _conn.noop()
            return _conn
        except Exception:
            logger.warning("[GMAIL] Connection dead, reconnecting…")
            _conn = None
    _conn = _connect()
    return _conn


def _reset_conn():
    """Discard the connection after an error so the next call reconnects."""
    global _conn
    try:
        if _conn:
            _conn.logout()
    except Exception:
        pass
    _conn = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _decode_header(raw) -> str:
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _get_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return body.strip()


def _get_attachments(msg: email.message.Message) -> list[dict]:
    attachments = []
    for part in msg.walk():
        disp = str(part.get("Content-Disposition", ""))
        if "attachment" in disp:
            filename = _decode_header(part.get_filename() or "")
            size = len(part.get_payload(decode=True) or b"")
            attachments.append({
                "filename": filename,
                "size_kb": round(size / 1024, 1),
                "content_type": part.get_content_type(),
            })
    return attachments


def _tag_email(subject: str, body: str, msg=None) -> str:
    """Classify email using Gemini. Falls back to keyword check if Gemini is unavailable."""
    # Skip bulk/marketing emails immediately — no LLM call needed
    if msg is not None:
        if msg.get("List-Unsubscribe") or msg.get("List-ID") or msg.get("Precedence") == "bulk":
            return "General"

    try:
        return _tag_email_llm(subject, body)
    except Exception as exc:
        logger.warning(f"[GMAIL] LLM email tagging failed, using keyword fallback: {exc}")
        return _tag_email_keywords(subject, body)


def _tag_email_llm(subject: str, body: str) -> str:
    """Use Gemini Flash to classify the email intent."""
    from models.gemini_models import get_gemini
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_gemini(temperature=0)
    clean_body = re.sub(r"https?://\S+", " ", body or "")[:1500]

    prompt = """Classify this email into exactly one category. Reply with only the category name, nothing else.

Categories:
- RFQ: sender wants a price quote, product pricing, or to purchase goods/services
- Order: confirmed purchase order or order update
- Follow-up: chasing a previous quote or conversation
- Complaint: issue, damage, wrong item, or dissatisfaction
- General: anything else (notifications, marketing, newsletters, personal messages)

Email:
Subject: {subject}
Body: {body}

Reply with one word only: RFQ, Order, Follow-up, Complaint, or General""".format(
        subject=subject, body=clean_body
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    tag = content.strip().split()[0]
    valid = {"RFQ", "Order", "Follow-up", "Complaint", "General"}
    return tag if tag in valid else "General"


def _tag_email_keywords(subject: str, body: str) -> str:
    """Keyword fallback when LLM is unavailable."""
    subject_lower = subject.lower()
    clean_body = re.sub(r"https?://\S+", " ", body or "").lower()
    text = subject_lower + " " + clean_body

    if re.search(r"\brfq\b", text) or any(w in text for w in ["request for quotation", "quotation request", "quote request"]):
        return "RFQ"
    if any(w in subject_lower for w in ["inquiry", "enquiry", "pricing request"]):
        return "RFQ"
    if any(w in text for w in ["order confirmation", "purchase order"]):
        return "Order"
    if any(w in text for w in ["follow up", "follow-up", "reminder"]):
        return "Follow-up"
    if any(w in text for w in ["complaint", "damaged", "wrong item"]):
        return "Complaint"
    return "General"


# ── Public API ───────────────────────────────────────────────────────────────

def list_emails(folder: str = "INBOX", limit: int = 25) -> list[dict]:
    """Return a list of email summaries from the inbox (single batched FETCH)."""
    with _lock:
        try:
            imap = _get_conn()
            imap.select(folder, readonly=True)
            _, data = imap.search(None, "ALL")
            ids = data[0].split()
            ids = ids[-limit:][::-1]  # most recent first

            if not ids:
                return []

            # Single FETCH command for all message IDs — avoids N round-trips
            msg_set = b",".join(ids)
            _, msg_data = imap.fetch(msg_set, "(RFC822.SIZE FLAGS X-GM-THRID X-GM-MSGID BODY.PEEK[HEADER])")

            # Build a map from UID → parsed result; imaplib interleaves tuples
            by_id: dict[bytes, dict] = {}
            i = 0
            while i < len(msg_data):
                item = msg_data[i]
                if not isinstance(item, tuple):
                    i += 1
                    continue
                meta_line = item[0].decode()
                raw_header = item[1]
                i += 1

                # Extract numeric UID from the FETCH response line
                uid_match = re.search(r"^(\d+) ", meta_line)
                if not uid_match:
                    continue
                uid = uid_match.group(1).encode()

                size_match = re.search(r"RFC822\.SIZE (\d+)", meta_line)
                size = int(size_match.group(1)) if size_match else 0
                unread = "\\Seen" not in meta_line

                thread_match = re.search(r"X-GM-THRID (\d+)", meta_line)
                thread_id = thread_match.group(1) if thread_match else None

                # Use Gmail REST-compatible hex ID so links are consistent with REST inbox
                msgid_match = re.search(r"X-GM-MSGID (\d+)", meta_line)
                gmail_id = hex(int(msgid_match.group(1)))[2:] if msgid_match else uid.decode()

                msg = email.message_from_bytes(raw_header)
                subject = _decode_header(msg.get("Subject", "(No Subject)"))
                from_raw = msg.get("From", "")
                name, addr = email.utils.parseaddr(from_raw)
                name = _decode_header(name) if name else addr.split("@")[0]
                date_str = msg.get("Date", "")
                try:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
                    date_iso = dt.isoformat()
                except Exception:
                    date_fmt = date_str
                    date_iso = ""

                by_id[uid] = {
                    "id": gmail_id,
                    "subject": subject,
                    "from_name": name or addr,
                    "from_email": addr,
                    "date": date_fmt,
                    "date_iso": date_iso,
                    "unread": unread,
                    "size_kb": round(size / 1024, 1),
                    "tag": _tag_email_keywords(subject, ""),
                    "preview": "",
                    "thread_id": thread_id,
                }

            # Return in original order (most-recent first)
            emails = [by_id[uid] for uid in ids if uid in by_id]
            logger.info(f"[GMAIL] list_emails: returned {len(emails)} emails")
            return emails
        except Exception as e:
            logger.error(f"[GMAIL] list_emails failed: {e}")
            _reset_conn()
            raise


def list_emails_rest(creds, folder: str = "INBOX", limit: int = 25) -> list[dict]:
    """
    List emails via Gmail REST API — much faster than IMAP, no persistent connection.
    Uses batch metadata fetch: one messages.list call + parallel messages.get calls.
    """
    from googleapiclient.discovery import build
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    # Build a thread-local service to avoid sharing the httplib2 connection pool
    # across threads (causes SSL: WRONG_VERSION_NUMBER errors)
    _local = threading.local()

    def _get_service():
        if not hasattr(_local, "svc"):
            _local.svc = build("gmail", "v1", credentials=creds)
        return _local.svc

    label = "INBOX" if folder.upper() == "INBOX" else folder
    result = _get_service().users().messages().list(
        userId="me", labelIds=[label], maxResults=limit
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        return []

    def fetch_meta(msg_id: str) -> dict | None:
        try:
            m = _get_service().users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["Subject", "From", "Date", "List-Unsubscribe", "List-ID"],
            ).execute()

            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "(No Subject)")
            from_raw = headers.get("From", "")
            name, addr = email.utils.parseaddr(from_raw)
            name = _decode_header(name) if name else addr.split("@")[0]
            date_str = headers.get("Date", "")
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
                date_iso = dt.isoformat()
            except Exception:
                date_fmt = date_str
                date_iso = ""

            unread = "UNREAD" in m.get("labelIds", [])
            thread_id = m.get("threadId")
            snippet = m.get("snippet", "")

            has_unsub = bool(headers.get("List-Unsubscribe") or headers.get("List-ID"))

            return {
                "id": msg_id,
                "subject": _decode_header(subject),
                "from_name": name or addr,
                "from_email": addr,
                "date": date_fmt,
                "date_iso": date_iso,
                "unread": unread,
                "size_kb": round(m.get("sizeEstimate", 0) / 1024, 1),
                "tag": "General" if has_unsub else _tag_email_keywords(_decode_header(subject), snippet),
                "preview": snippet,
                "thread_id": thread_id,
            }
        except Exception as exc:
            logger.warning(f"[GMAIL REST] Failed to fetch message {msg_id}: {exc}")
            return None

    emails = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_meta, m["id"]): m["id"] for m in messages}
        results = {fid: f.result() for f, fid in [(f, futures[f]) for f in as_completed(futures)]}

    # Preserve original order
    for m in messages:
        item = results.get(m["id"])
        if item:
            emails.append(item)

    logger.info(f"[GMAIL REST] Fetched {len(emails)} emails")
    return emails


def list_emails_oauth(email_addr: str, access_token: str, folder: str = "INBOX", limit: int = 25) -> list[dict]:
    """Same as list_emails but connects via XOAUTH2 for a connected account."""
    imap = _connect_oauth(email_addr, access_token)
    try:
        imap.select(folder, readonly=True)
        _, data = imap.search(None, "ALL")
        ids = data[0].split()
        ids = ids[-limit:][::-1]

        if not ids:
            return []

        msg_set = b",".join(ids)
        _, msg_data = imap.fetch(msg_set, "(RFC822.SIZE FLAGS X-GM-THRID X-GM-MSGID BODY.PEEK[HEADER])")

        by_id: dict[bytes, dict] = {}
        i = 0
        while i < len(msg_data):
            item = msg_data[i]
            if not isinstance(item, tuple):
                i += 1
                continue
            meta_line = item[0].decode()
            raw_header = item[1]
            i += 1

            uid_match = re.search(r"^(\d+) ", meta_line)
            if not uid_match:
                continue
            uid = uid_match.group(1).encode()

            size_match = re.search(r"RFC822\.SIZE (\d+)", meta_line)
            size = int(size_match.group(1)) if size_match else 0
            unread = "\\Seen" not in meta_line

            thread_match = re.search(r"X-GM-THRID (\d+)", meta_line)
            thread_id = thread_match.group(1) if thread_match else None

            msgid_match = re.search(r"X-GM-MSGID (\d+)", meta_line)
            gmail_id = hex(int(msgid_match.group(1)))[2:] if msgid_match else uid.decode()

            msg = email.message_from_bytes(raw_header)
            subject = _decode_header(msg.get("Subject", "(No Subject)"))
            from_raw = msg.get("From", "")
            name, addr = email.utils.parseaddr(from_raw)
            name = _decode_header(name) if name else addr.split("@")[0]
            date_str = msg.get("Date", "")
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
                date_iso = dt.isoformat()
            except Exception:
                date_fmt = date_str
                date_iso = ""

            by_id[uid] = {
                "id": gmail_id,
                "subject": subject,
                "from_name": name or addr,
                "from_email": addr,
                "date": date_fmt,
                "date_iso": date_iso,
                "unread": unread,
                "size_kb": round(size / 1024, 1),
                "tag": _tag_email_keywords(subject, ""),
                "preview": "",
                "thread_id": thread_id,
            }

        return [by_id[uid] for uid in ids if uid in by_id]
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def get_email_rest(creds, email_id: str) -> dict:
    """Fetch a single email via Gmail REST API (used when listing was done via REST)."""
    from googleapiclient.discovery import build
    import base64

    service = build("gmail", "v1", credentials=creds)
    m = service.users().messages().get(userId="me", id=email_id, format="full").execute()

    headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
    subject = _decode_header(headers.get("Subject", "(No Subject)"))
    from_raw = headers.get("From", "")
    name, addr = email.utils.parseaddr(from_raw)
    name = _decode_header(name) if name else addr.split("@")[0]

    date_str = headers.get("Date", "")
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
        date_iso = dt.isoformat()
    except Exception:
        date_fmt = date_str
        date_iso = ""

    def _extract_parts(payload):
        """Recursively extract text/plain body from MIME parts."""
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = _extract_parts(part)
            if result:
                return result
        return ""

    body = _extract_parts(m.get("payload", {})).strip()

    # Collect attachments
    attachments = []
    def _collect_attachments(payload):
        disp = ""
        for h in payload.get("headers", []):
            if h["name"].lower() == "content-disposition":
                disp = h["value"]
        filename = payload.get("filename", "")
        if filename and "attachment" in disp.lower():
            size = payload.get("body", {}).get("size", 0)
            attachments.append({
                "filename": filename,
                "size_kb": round(size / 1024, 1),
                "content_type": payload.get("mimeType", ""),
            })
        for part in payload.get("parts", []):
            _collect_attachments(part)

    _collect_attachments(m.get("payload", {}))

    return {
        "id": email_id,
        "subject": subject,
        "from_name": name or addr,
        "from_email": addr,
        "date": date_fmt,
        "date_iso": date_iso,
        "body": body,
        "preview": body[:200].replace("\n", " ") if body else m.get("snippet", ""),
        "attachments": attachments,
        "tag": _tag_email_keywords(subject, body),
        "thread_id": m.get("threadId"),
    }


def get_thread_emails_rest(creds, thread_id: str) -> list[dict]:
    """Fetch all emails in a Gmail thread via REST API."""
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    result = []
    for m in thread.get("messages", []):
        try:
            msg_id = m["id"]
            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            subject = _decode_header(headers.get("Subject", "(No Subject)"))
            from_raw = headers.get("From", "")
            name, addr = email.utils.parseaddr(from_raw)
            name = _decode_header(name) if name else addr.split("@")[0]

            date_str = headers.get("Date", "")
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
                date_iso = dt.isoformat()
            except Exception:
                date_fmt = date_str
                date_iso = ""

            import base64

            def _extract_parts(payload):
                mime = payload.get("mimeType", "")
                if mime == "text/plain":
                    data = payload.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                for part in payload.get("parts", []):
                    r = _extract_parts(part)
                    if r:
                        return r
                return ""

            body = _extract_parts(m.get("payload", {})).strip()

            attachments = []

            def _collect_attachments(payload):
                disp = ""
                for h in payload.get("headers", []):
                    if h["name"].lower() == "content-disposition":
                        disp = h["value"]
                filename = payload.get("filename", "")
                if filename and "attachment" in disp.lower():
                    size = payload.get("body", {}).get("size", 0)
                    attachments.append({
                        "filename": filename,
                        "size_kb": round(size / 1024, 1),
                        "content_type": payload.get("mimeType", ""),
                    })
                for part in payload.get("parts", []):
                    _collect_attachments(part)

            _collect_attachments(m.get("payload", {}))

            result.append({
                "id": msg_id,
                "subject": subject,
                "from_name": name or addr,
                "from_email": addr,
                "date": date_fmt,
                "date_iso": date_iso,
                "body": body,
                "preview": body[:200].replace("\n", " ") if body else m.get("snippet", ""),
                "attachments": attachments,
                "tag": _tag_email_keywords(subject, body),
                "thread_id": thread_id,
            })
        except Exception as exc:
            logger.warning(f"[GMAIL REST] Failed to parse thread message {m.get('id')}: {exc}")

    return result


def get_email_oauth(email_addr: str, access_token: str, email_id: str) -> dict:
    """Fetch a single email via XOAUTH2 IMAP (only for integer IMAP sequence IDs)."""
    imap = _connect_oauth(email_addr, access_token)
    try:
        imap.select("INBOX", readonly=True)
        return _fetch_email(imap, email_id)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def _resolve_imap_id(imap, email_id: str) -> str:
    """Convert a hex Gmail REST message ID to an IMAP sequence number if needed."""
    if email_id.isdigit():
        return email_id
    # hex REST ID → decimal X-GM-MSGID → IMAP search
    decimal_id = str(int(email_id, 16))
    _, data = imap.search(None, f"X-GM-MSGID {decimal_id}")
    ids = data[0].split()
    return ids[0].decode() if ids else email_id


def _fetch_email(imap, email_id: str) -> dict:
    """Shared fetch logic for both app-password and OAuth connections."""
    imap_id = _resolve_imap_id(imap, email_id)
    _, msg_data = imap.fetch(imap_id.encode(), "(RFC822 X-GM-THRID)")
    if not msg_data or msg_data[0] is None:
        raise RuntimeError(f"Email {email_id} not found")
    meta_line = msg_data[0][0].decode()
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)

    thread_match = re.search(r"X-GM-THRID (\d+)", meta_line)
    thread_id = thread_match.group(1) if thread_match else None

    subject = _decode_header(msg.get("Subject", "(No Subject)"))
    from_raw = msg.get("From", "")
    name, addr = email.utils.parseaddr(from_raw)
    name = _decode_header(name) if name else addr.split("@")[0]

    date_str = msg.get("Date", "")
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
        date_iso = dt.isoformat()
    except Exception:
        date_fmt = date_str
        date_iso = ""

    body = _get_body(msg)
    attachments = _get_attachments(msg)
    tag = _tag_email_keywords(subject, body)

    return {
        "id": email_id,
        "subject": subject,
        "from_name": name or addr,
        "from_email": addr,
        "date": date_fmt,
        "date_iso": date_iso,
        "body": body,
        "preview": body[:200].replace("\n", " ") if body else "",
        "attachments": attachments,
        "tag": tag,
        "thread_id": thread_id,
    }


def get_email(email_id: str) -> dict:
    """Fetch full email content via app password IMAP."""
    with _lock:
        try:
            imap = _get_conn()
            imap.select("INBOX", readonly=True)
            return _fetch_email(imap, email_id)
        except Exception as e:
            logger.error(f"[GMAIL] get_email({email_id}) failed: {e}")
            _reset_conn()
            raise


def get_email_attachments_with_bytes(email_id: str) -> list[dict]:
    """Return attachments with actual binary content for extraction."""
    with _lock:
        try:
            imap = _get_conn()
            imap.select("INBOX", readonly=True)
            _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            attachments = []
            for part in msg.walk():
                disp = str(part.get("Content-Disposition", ""))
                if "attachment" not in disp:
                    continue
                filename = _decode_header(part.get_filename() or "")
                payload = part.get_payload(decode=True)
                if payload and filename:
                    attachments.append({
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "bytes": payload,
                    })
            return attachments
        except Exception as e:
            logger.error(f"[GMAIL] get_email_attachments_with_bytes({email_id}) failed: {e}")
            _reset_conn()
            return []


def mark_as_read(email_id: str):
    with _lock:
        try:
            imap = _get_conn()
            imap.select("INBOX")
            imap.store(email_id.encode(), "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error(f"[GMAIL] mark_as_read failed: {e}")
            _reset_conn()


def get_thread_emails(thread_id: str) -> list[dict]:
    """Fetch full email content (including body and attachments) for all emails in the same thread."""
    if not thread_id:
        return []
    with _lock:
        try:
            imap = _get_conn()
            imap.select("INBOX", readonly=True)
            _, data = imap.search(None, "X-GM-THRID", thread_id)
            ids = data[0].split()
            if not ids:
                return []

            # Fetch all messages in the thread
            msg_set = b",".join(ids)
            _, msg_data = imap.fetch(msg_set, "(RFC822 X-GM-THRID)")

            emails_list = []

            # Parse each message
            i = 0
            while i < len(msg_data):
                item = msg_data[i]
                if not isinstance(item, tuple):
                    i += 1
                    continue
                meta_line = item[0].decode()
                raw = item[1]
                i += 1

                uid_match = re.search(r"^(\d+) ", meta_line)
                if not uid_match:
                    continue
                uid = uid_match.group(1)

                msg = email.message_from_bytes(raw)
                subject = _decode_header(msg.get("Subject", "(No Subject)"))
                from_raw = msg.get("From", "")
                name, addr = email.utils.parseaddr(from_raw)
                name = _decode_header(name) if name else addr.split("@")[0]

                date_str = msg.get("Date", "")
                try:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    date_fmt = dt.strftime("%d %b %Y, %I:%M %p")
                    date_iso = dt.isoformat()
                except Exception:
                    date_fmt = date_str
                    date_iso = ""

                body = _get_body(msg)
                attachments = _get_attachments(msg)
                tag = _tag_email_keywords(subject, body)

                emails_list.append({
                    "id": uid,
                    "subject": subject,
                    "from_name": name or addr,
                    "from_email": addr,
                    "date": date_fmt,
                    "date_iso": date_iso,
                    "body": body,
                    "preview": body[:200].replace("\n", " ") if body else "",
                    "attachments": attachments,
                    "tag": tag,
                    "thread_id": thread_id,
                })

            # Sort chronologically by sequence ID
            id_order = {uid.decode(): idx for idx, uid in enumerate(ids)}
            emails_list.sort(key=lambda x: id_order.get(x["id"], 9999))

            return emails_list
        except Exception as e:
            logger.error(f"[GMAIL] get_thread_emails({thread_id}) failed: {e}")
            _reset_conn()
            return []
