from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool, text
from alembic import context
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from db.database import Base
from db.models import (  # noqa: F401 — register all tables with metadata
    Plan, Firm, Resource, Lead,
    InteriorProfile, RealEstateProfile, SolarProfile,
    Session, Visit, ConversationLog, RetrievalLog,
    FollowupSchedule, BroadcastCampaign, BroadcastSend,
)
from db.config import SCHEMA

alembic_cfg = context.config

if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Override URL from env — alembic uses sync psycopg2, strip async drivers
raw_url = os.environ.get("DATABASE_URL", "")
for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgres://"):
    if raw_url.startswith(prefix):
        raw_url = "postgresql://" + raw_url[len(prefix):]
        break
if raw_url:
    alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "sqlalchemy.url", raw_url)

target_metadata = Base.metadata


def _include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=_include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        context.config.get_section(context.config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.execute(text(f'SET search_path TO "{SCHEMA}"'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_name=_include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
