"""
Supabase service — Storage operations only.

All DB reads/writes now go through db/crud.py (SQLAlchemy async).
This module handles Supabase Storage (PDF uploads) and the Supabase
Python client for anything that doesn't have a SQLAlchemy equivalent.
"""

import logging

from supabase import create_client, Client

from config import settings

log = logging.getLogger(__name__)

_client: Client | None = None


def init() -> None:
    """Call once from FastAPI lifespan."""
    global _client
    _client = create_client(settings.supabase_url, settings.supabase_service_key)
    log.info("Supabase Storage client initialised")


def _sb() -> Client:
    assert _client, "supabase_svc.init() not called"
    return _client


async def upload_file(bucket: str, path: str, data: bytes, content_type: str = "application/pdf") -> str:
    """Upload a file to Supabase Storage. Returns the public URL."""
    import asyncio

    def _run():
        _sb().storage.from_(bucket).upload(path, data, {"content-type": content_type})
        return _sb().storage.from_(bucket).get_public_url(path)

    return await asyncio.to_thread(_run)


async def delete_file(bucket: str, path: str) -> None:
    import asyncio
    await asyncio.to_thread(lambda: _sb().storage.from_(bucket).remove([path]))
