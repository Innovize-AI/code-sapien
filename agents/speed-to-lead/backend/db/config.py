import os
import logging

logger = logging.getLogger(__name__)

from dotenv import load_dotenv


def _load_dotenv():
    current = os.path.dirname(os.path.abspath(__file__))
    for d in [current, os.path.dirname(current)]:
        env_path = os.path.join(d, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return


_load_dotenv()

raw_url = os.getenv("DATABASE_URL", "")

def _fix_url(url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url

DATABASE_URL = _fix_url(raw_url)

SCHEMA = "stl"

_is_pooler = "pooler.supabase.com" in DATABASE_URL
