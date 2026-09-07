"""
Gmail OAuth connect/disconnect routes for multi-account inbox monitoring.

GET  /api/auth/gmail               → redirect to Google consent
GET  /api/auth/gmail/callback      → handle OAuth callback, save token, register watch
GET  /api/auth/accounts            → list connected accounts
DELETE /api/auth/accounts/{email}  → disconnect account
"""
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.database import get_db
from db.models import ConnectedAccount

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

_PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "")
_BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
_REDIRECT_URI = f"{_BACKEND_URL}/api/auth/gmail/callback"
_FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")[0].strip())

# In-memory store for pending OAuth flows (state → flow object)
# Flows are short-lived — cleaned up after callback
_pending_flows: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Start OAuth flow
# ---------------------------------------------------------------------------

@router.get("/auth/gmail")
async def gmail_connect():
    """Redirect the browser to Google's OAuth consent screen."""
    from services.gmail_oauth import get_oauth_flow, credentials_configured

    if not credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_OAUTH_CREDENTIALS env var not set. Paste the contents of credentials.json into this variable.",
        )

    flow = get_oauth_flow(_REDIRECT_URI)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Store the flow so the callback can reuse it (preserves code_verifier)
    _pending_flows[state] = flow
    return RedirectResponse(auth_url)


# ---------------------------------------------------------------------------
# OAuth callback
# ---------------------------------------------------------------------------

@router.get("/auth/gmail/callback")
async def gmail_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Exchange auth code for token, save to DB, register Gmail watch."""
    from services.gmail_oauth import get_oauth_flow, register_gmail_watch
    from googleapiclient.discovery import build

    # Retrieve the original flow to preserve code_verifier for PKCE
    flow = _pending_flows.pop(state, None)
    if not flow:
        flow = get_oauth_flow(_REDIRECT_URI)

    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}")

    creds = flow.credentials
    token_json = creds.to_json()

    # Get the email address of the account that just connected
    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile["emailAddress"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch Gmail profile: {exc}")

    # Register Gmail push watch
    watch_expiry = None
    if _PUBSUB_TOPIC:
        try:
            result = register_gmail_watch(creds, email, _PUBSUB_TOPIC)
            history_id = result.get("historyId")
            exp_ms = result.get("expiration")
            if exp_ms:
                watch_expiry = datetime.fromtimestamp(int(exp_ms) / 1000, tz=timezone.utc)
            logger.info(f"[AUTH] Gmail watch registered for {email} expires={watch_expiry}")
        except Exception as exc:
            logger.warning(f"[AUTH] Gmail watch registration failed for {email}: {exc}")
            history_id = None
    else:
        history_id = None
        logger.warning("[AUTH] PUBSUB_TOPIC not set — Gmail watch skipped, falling back to IMAP polling")

    # Upsert into connected_accounts
    result = await db.execute(select(ConnectedAccount).where(ConnectedAccount.email == email))
    account = result.scalars().first()

    if account:
        account.token_json = token_json
        account.watch_expiry = watch_expiry
        account.history_id = history_id
        account.active = True
    else:
        account = ConnectedAccount(
            email=email,
            token_json=token_json,
            watch_expiry=watch_expiry,
            history_id=history_id,
            active=True,
        )
        db.add(account)

    await db.commit()
    logger.info(f"[AUTH] Account connected: {email}")

    # Redirect back to frontend settings page
    return RedirectResponse(f"{_FRONTEND_URL}/settings?connected={email}")


# ---------------------------------------------------------------------------
# List connected accounts
# ---------------------------------------------------------------------------

@router.get("/auth/accounts")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConnectedAccount).order_by(ConnectedAccount.created_at))
    accounts = result.scalars().all()
    return {
        "accounts": [
            {
                "email": a.email,
                "active": a.active,
                "watch_expiry": a.watch_expiry.isoformat() if a.watch_expiry else None,
                "connected_at": a.created_at.isoformat(),
            }
            for a in accounts
        ]
    }


# ---------------------------------------------------------------------------
# Disconnect account
# ---------------------------------------------------------------------------

@router.delete("/auth/accounts/{email}")
async def disconnect_account(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConnectedAccount).where(ConnectedAccount.email == email))
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Stop Gmail watch
    from services.gmail_oauth import credentials_from_token_json, unregister_gmail_watch
    creds = credentials_from_token_json(account.token_json)
    if creds:
        unregister_gmail_watch(creds, email)

    await db.execute(delete(ConnectedAccount).where(ConnectedAccount.email == email))
    await db.commit()
    logger.info(f"[AUTH] Account disconnected: {email}")
    return {"status": "disconnected", "email": email}
