import base64
import os
import logging
import smtplib
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GMAIL_SENDER       = os.getenv("GMAIL_SENDER") or os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASSWORD", "")
COMPANY_NAME       = os.getenv("COMPANY_NAME", "Our Company")

DRAFT_USER     = os.getenv("GMAIL_DRAFT_USER") or os.getenv("GMAIL_USER_SAI", "")
DRAFT_PASSWORD = os.getenv("GMAIL_DRAFT_PASSWORD", "")

_TOKEN_PATH = Path(__file__).resolve().parent.parent / "gmail_token.json"
_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _oauth_credentials():
    """Return valid OAuth credentials if gmail_token.json exists, else None."""
    if not _TOKEN_PATH.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _OAUTH_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _TOKEN_PATH.write_text(creds.to_json())
        return creds if creds.valid else None
    except Exception as exc:
        logger.warning(f"[EMAIL] OAuth credential load failed: {exc}")
        return None


def _send_via_oauth(msg: MIMEMultipart, to: str, rfq_id: str) -> bool:
    """Send using Gmail API (OAuth). Returns True on success."""
    creds = _oauth_credentials()
    if not creds:
        return False
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"[EMAIL] Quotation sent via OAuth to {to} (RFQ {rfq_id})")
        return True
    except Exception as exc:
        logger.warning(f"[EMAIL] OAuth send failed, will try SMTP: {exc}")
        return False


def _send_via_smtp(msg: MIMEMultipart, to: str, rfq_id: str) -> bool:
    """Send using SMTP + app password. Returns True on success."""
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.warning("[EMAIL] GMAIL_SENDER or GMAIL_APP_PASSWORD not configured — skipping SMTP send")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, to, msg.as_string())
        logger.info(f"[EMAIL] Quotation sent via SMTP to {to} (RFQ {rfq_id})")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] Gmail SMTP authentication failed — check GMAIL_SENDER and GMAIL_APP_PASSWORD")
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"[EMAIL] Recipient refused: {to}")
    except Exception as exc:
        logger.error(f"[EMAIL] SMTP send failed for RFQ {rfq_id}: {exc}")
    return False


def send_quotation_email(
    to: str,
    rfq_id: str,
    buyer_name: str,
    draft_quote: str,
    total: float,
    pdf_bytes: Optional[bytes] = None,
    excel_bytes: Optional[bytes] = None,
    excel_filename: Optional[str] = None,
) -> bool:
    """
    Send a quotation email. Tries OAuth (Gmail API) first, falls back to SMTP app password.
    Returns True on success, False on failure.
    """

    subject = f"Quotation from {COMPANY_NAME} — Ref {rfq_id[:8].upper()}"

    html_body = _build_html(buyer_name, rfq_id, draft_quote, total)
    plain_body = _build_plain(buyer_name, rfq_id, draft_quote, total)

    # Use "mixed" so we can carry both html and binary attachments
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = f"{COMPANY_NAME} <{GMAIL_SENDER}>"
    msg["To"]      = to
    msg["Reply-To"] = GMAIL_SENDER

    # Body part (plain + html as alternative)
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(plain_body, "plain"))
    body_part.attach(MIMEText(html_body,  "html"))
    msg.attach(body_part)

    # PDF attachment
    if pdf_bytes:
        pdf_part = MIMEBase("application", "pdf")
        pdf_part.set_payload(pdf_bytes)
        encoders.encode_base64(pdf_part)
        filename = f"Quotation-{rfq_id[:8].upper()}.pdf"
        pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(pdf_part)
        logger.info(f"[EMAIL] Attaching PDF ({len(pdf_bytes)//1024}KB) to quotation for {to}")

    # Excel attachment
    if excel_bytes and excel_filename:
        excel_part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        excel_part.set_payload(excel_bytes)
        encoders.encode_base64(excel_part)
        excel_part.add_header("Content-Disposition", "attachment", filename=excel_filename)
        msg.attach(excel_part)
        logger.info(f"[EMAIL] Attaching filled Excel template ({len(excel_bytes)//1024}KB) to quotation for {to}")

    return _send_via_oauth(msg, to, rfq_id) or _send_via_smtp(msg, to, rfq_id)


def send_review_alert_email(rfq_id: str, sender: str, review_notes: str, total: float):
    """Send an internal alert to the reviewer when an RFQ needs human review."""
    reviewer_email = os.getenv("REVIEWER_EMAIL", "")
    if not reviewer_email or not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.warning("[EMAIL] Reviewer alert skipped — email not configured")
        return

    subject = f"[Review Required] RFQ {rfq_id[:8].upper()} from {sender}"

    html = f"""
    <html><body style="font-family:sans-serif;color:#333;max-width:600px;margin:auto">
      <h2 style="color:#d97706">⚠ RFQ Needs Review</h2>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;font-weight:bold">RFQ ID</td><td style="padding:6px">{rfq_id}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:6px;font-weight:bold">From</td><td style="padding:6px">{sender}</td></tr>
        <tr><td style="padding:6px;font-weight:bold">Estimated Total</td><td style="padding:6px">₹{total:,.2f}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:6px;font-weight:bold">Reason</td><td style="padding:6px;color:#dc2626">{review_notes}</td></tr>
      </table>
      <p style="margin-top:20px">Please log in to review and approve or reject this quotation.</p>
      <p style="color:#6b7280;font-size:12px">Sent by {COMPANY_NAME} RFQ Agent</p>
    </body></html>
    """

    plain = f"RFQ Review Required\n\nRFQ ID: {rfq_id}\nFrom: {sender}\nTotal: Rs {total:,.2f}\nReason: {review_notes}\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{COMPANY_NAME} RFQ Agent <{GMAIL_SENDER}>"
    msg["To"]      = reviewer_email

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    if not (_send_via_oauth(msg, reviewer_email, rfq_id) or _send_via_smtp(msg, reviewer_email, rfq_id)):
        logger.error(f"[EMAIL] Review alert failed for RFQ {rfq_id}")


# ---------------------------------------------------------------------------
# Email body builders
# ---------------------------------------------------------------------------

def _build_plain(buyer_name: str, rfq_id: str, draft_quote: str, total: float) -> str:
    return (
        f"Dear {buyer_name or 'Valued Customer'},\n\n"
        f"Please find below our quotation in response to your RFQ (Ref: {rfq_id[:8].upper()}).\n\n"
        f"{draft_quote}\n\n"
        f"Estimated Total: Rs {total:,.2f}\n\n"
        f"This quotation is valid for 30 days from {date.today().strftime('%d %B %Y')}.\n\n"
        f"Regards,\n{COMPANY_NAME}"
    )


def _build_html(buyer_name: str, rfq_id: str, draft_quote: str, total: float) -> str:
    import markdown
    if draft_quote:
        quote_html = markdown.markdown(draft_quote, extensions=['tables'])
        # Inject inline styling for bulletproof rendering in Outlook/Gmail/Apple Mail
        quote_html = quote_html.replace("<table>", '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-family:Arial,sans-serif;font-size:13px;">')
        quote_html = quote_html.replace("<th>", '<th style="border:1px solid #e5e7eb;padding:8px 12px;text-align:left;background-color:#f9fafb;font-weight:bold;color:#374151;">')
        quote_html = quote_html.replace("<td>", '<td style="border:1px solid #e5e7eb;padding:8px 12px;text-align:left;color:#4b5563;">')
        quote_html = quote_html.replace("<tr>", '<tr style="border-bottom:1px solid #e5e7eb;">')
        quote_html = quote_html.replace("<ul>", '<ul style="padding-left:20px;margin:8px 0;color:#4b5563;">')
        quote_html = quote_html.replace("<ol>", '<ol style="padding-left:20px;margin:8px 0;color:#4b5563;">')
        quote_html = quote_html.replace("<li>", '<li style="margin-bottom:4px;">')
        quote_html = quote_html.replace("<p>", '<p style="margin:0 0 8px;line-height:1.5;color:#4b5563;">')
    else:
        quote_html = "Please see attached quotation."

    today = date.today().strftime("%d %b %Y")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:680px;margin:auto;padding:20px">

  <div style="background:#1e40af;padding:24px 32px;border-radius:8px 8px 0 0">
    <h1 style="color:#fff;margin:0;font-size:22px">{COMPANY_NAME}</h1>
    <p style="color:#bfdbfe;margin:4px 0 0">Quotation · Ref {rfq_id[:8].upper()}</p>
  </div>

  <div style="border:1px solid #e5e7eb;border-top:none;padding:32px;border-radius:0 0 8px 8px">

    <p>Dear <strong>{buyer_name or 'Valued Customer'}</strong>,</p>
    <p>Thank you for your enquiry. Please find our quotation below.</p>

    <div style="background:#f8fafc;border-left:4px solid #1e40af;padding:20px;border-radius:4px;margin:24px 0;font-size:14px;line-height:1.6">
{quote_html}
    </div>

    <table style="width:100%;border-collapse:collapse;margin-top:16px">
      <tr style="background:#1e40af;color:#fff">
        <td style="padding:10px 16px;font-weight:bold">Estimated Total</td>
        <td style="padding:10px 16px;text-align:right;font-size:18px;font-weight:bold">₹{total:,.2f}</td>
      </tr>
    </table>

    <p style="margin-top:24px;font-size:13px;color:#6b7280">
      This quotation is valid for 30 days from <strong>{today}</strong>.<br>
      To proceed, please reply to this email or contact us directly.
    </p>

    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
    <p style="font-size:12px;color:#9ca3af;text-align:center">
      {COMPANY_NAME} · {GMAIL_SENDER}
    </p>
  </div>
</body>
</html>
"""
