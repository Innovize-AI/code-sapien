"""
Gmail OAuth helpers — load/save/refresh credentials per connected account.
Tokens are stored as JSON in the connected_accounts DB table.

OAuth client credentials are read from the GOOGLE_OAUTH_CREDENTIALS env var
(JSON string — paste the contents of credentials.json).
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

SCOPES = [
    "https://mail.google.com/",          # IMAP + SMTP XOAUTH2 access
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _client_config() -> dict:
    """Load OAuth client config from env var."""
    raw = os.getenv("GOOGLE_OAUTH_CREDENTIALS", "")
    if not raw:
        raise RuntimeError(
            "GOOGLE_OAUTH_CREDENTIALS env var not set. "
            "Paste the contents of your credentials.json into this variable."
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GOOGLE_OAUTH_CREDENTIALS is not valid JSON: {exc}")


def credentials_configured() -> bool:
    return bool(os.getenv("GOOGLE_OAUTH_CREDENTIALS", ""))


def credentials_from_token_json(token_json: str):
    """Deserialize and refresh a stored OAuth token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds if creds.valid else None
    except Exception as exc:
        logger.warning(f"[OAUTH] Failed to load credentials: {exc}")
        return None


def get_oauth_flow(redirect_uri: str):
    """Build an OAuth flow from the env var client config."""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


def register_gmail_watch(creds, email: str, pubsub_topic: str) -> dict:
    """Call gmail.watch() and return {historyId, expiration}."""
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    result = service.users().watch(
        userId=email,
        body={
            "topicName": pubsub_topic,
            "labelIds": ["INBOX"],
            "labelFilterBehavior": "INCLUDE",
        },
    ).execute()
    return result


def unregister_gmail_watch(creds, email: str):
    """Stop Gmail push notifications for this account."""
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        service.users().stop(userId=email).execute()
        logger.info(f"[OAUTH] Gmail watch stopped for {email}")
    except Exception as exc:
        logger.warning(f"[OAUTH] Could not stop Gmail watch for {email}: {exc}")
