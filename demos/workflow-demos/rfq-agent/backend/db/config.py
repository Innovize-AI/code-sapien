import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# backend/db/ → backend/ → rfq-agent/ → workflow-demos/
_wf_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_wf_env)

_local_env = Path(__file__).resolve().parent.parent / ".env"
if _local_env.exists():
    load_dotenv(_local_env, override=True)

os.environ.setdefault("DB_SCHEMA", "rfq")

raw_url = os.getenv("DATABASE_URL", "")

# Normalise to postgresql+psycopg:// for async SQLAlchemy (psycopg3).
# psycopg3 has no prepared-statement conflicts with PgBouncer transaction mode.
if raw_url.startswith("postgres://"):
    DATABASE_URL = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif raw_url.startswith("postgresql://"):
    DATABASE_URL = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = raw_url

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")
env = (os.getenv("ENVIRONMENT") or "dev").lower().strip()

logger.info(f"--- DB INITIALIZATION ---")
logger.info(f"ENV: {env}")
logger.info(f"SCHEMA: {DB_SCHEMA}")
logger.info(f"-------------------------")
