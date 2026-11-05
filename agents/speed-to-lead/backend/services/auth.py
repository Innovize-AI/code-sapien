"""
Who is calling the API.

The dashboard signs staff in through Supabase and sends the session's access token on every
request. We ask Supabase who the token belongs to (so there is no JWT secret to keep in sync),
read the role, firm and person from the user's metadata, and cache the answer for a minute.

Roles: admin and counselor see everything for their firm(s). An agent is a channel partner or
team member and sees only the conversations on their own numbers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from config import settings

log = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, "Actor | None"]] = {}
_TTL = 60.0


@dataclass
class Actor:
    user_id: str
    email: str
    role: str                    # admin | counselor | viewer | agent
    firm_id: str | None
    person_id: str | None
    name: str = ""

    @property
    def is_agent(self) -> bool:
        return self.role == "agent"


def actor_from_user(user: dict) -> Actor:
    meta = user.get("user_metadata") or {}
    return Actor(
        user_id=user.get("id", ""),
        email=user.get("email", ""),
        role=meta.get("role") or "viewer",
        firm_id=meta.get("firm_id"),
        person_id=meta.get("person_id"),
        name=meta.get("name") or user.get("email", ""),
    )


async def verify_token(token: str) -> Actor | None:
    """Returns the actor for a valid Supabase access token, or None."""
    now = time.monotonic()
    hit = _CACHE.get(token)
    if hit and hit[0] > now:
        return hit[1]

    key = settings.supabase_anon_key or settings.supabase_service_key
    actor: Actor | None = None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": key, "Authorization": f"Bearer {token}"},
            )
        if r.status_code == 200:
            actor = actor_from_user(r.json())
    except Exception as exc:
        log.warning("token check failed: %s", exc)
        return None            # do not cache a network failure

    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[token] = (now + _TTL, actor)
    return actor


async def create_login(email: str, password: str, *, role: str, firm_id: str, person_id: str,
                       name: str) -> str:
    """Create a Supabase sign-in for a person. Called by a counselor or admin from the dashboard.
    Returns the new user's id. Raises ValueError with a readable message on failure."""
    if len(password) < 8:
        raise ValueError("The password must be at least 8 characters")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
            headers={"apikey": settings.supabase_service_key,
                     "Authorization": f"Bearer {settings.supabase_service_key}"},
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": name, "role": role, "firm_id": firm_id, "person_id": person_id},
            },
        )
    if r.status_code in (200, 201):
        return r.json().get("id", "")
    detail = ""
    try:
        detail = r.json().get("msg") or r.json().get("message") or ""
    except Exception:
        pass
    if r.status_code in (409, 422) and ("registered" in detail.lower() or "exists" in detail.lower()):
        raise ValueError("That email already has an account")
    raise ValueError(detail or "Could not create the login")
