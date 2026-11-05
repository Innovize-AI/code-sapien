"""
Request guard shared by the dashboard routers.

  * guard: reads the sign-in token if there is one and rejects a bad one. With REQUIRE_AUTH=1
    every request must carry a valid token. Without it, requests that carry no token behave as
    they always did (local development, the simulators), so existing flows keep working.
  * deny_agents: for routes agents must never reach (admin screens, billing, firm settings).
  * scope helpers: an agent is limited to leads they own, enforced here and not in the browser.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services import auth


def _require_auth() -> bool:
    """In production every request must carry a valid sign-in, otherwise an agent could simply
    drop the token and read everything. Elsewhere it is off by default so local development and
    the simulators keep working. REQUIRE_AUTH=1 or 0 overrides either way."""
    explicit = os.getenv("REQUIRE_AUTH", "").strip().lower()
    if explicit in ("1", "true", "yes"):
        return True
    if explicit in ("0", "false", "no"):
        return False
    from config import settings
    return settings.is_production


async def guard(request: Request) -> auth.Actor | None:
    header = request.headers.get("authorization", "")
    actor = None
    if header.lower().startswith("bearer "):
        actor = await auth.verify_token(header[7:].strip())
        if actor is None:
            raise HTTPException(401, "Your session has expired. Sign in again.")
    elif _require_auth():
        raise HTTPException(401, "Sign in required")
    request.state.actor = actor
    return actor


async def deny_agents(actor: auth.Actor | None = Depends(guard)) -> auth.Actor | None:
    if actor is not None and actor.is_agent:
        raise HTTPException(403, "Your account cannot use this")
    return actor


def agent_person_id(actor: auth.Actor | None) -> UUID | None:
    """The person an agent is limited to, or None for staff who see everything."""
    if actor is not None and actor.is_agent:
        if not actor.person_id:
            raise HTTPException(403, "This account is not linked to a person")
        return UUID(actor.person_id)
    return None


async def ensure_lead_access(db: AsyncSession, actor: auth.Actor | None, lead_id: UUID) -> None:
    """Staff may open any lead. An agent may open only the leads on their own numbers."""
    person = agent_person_id(actor)
    if person is None:
        return
    from db.models import Lead
    lead = await db.get(Lead, lead_id)
    if lead is None or lead.owner_id != person:
        raise HTTPException(403, "This conversation belongs to someone else")


# Convenience dependency for routes that take an agent-aware actor and a session
async def actor_and_db(actor: auth.Actor | None = Depends(guard), db: AsyncSession = Depends(get_db)):
    return actor, db
