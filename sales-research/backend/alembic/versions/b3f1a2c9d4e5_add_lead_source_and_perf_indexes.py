"""Add lead_source column and performance indexes to identified_profiles

Revision ID: b3f1a2c9d4e5
Revises: a181011de66a
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1a2c9d4e5'
down_revision: Union[str, Sequence[str], None] = 'a181011de66a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONCURRENT_INDEXES = [
    # (index_name, ddl)
    ("ix_identified_profiles_lead_source",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_lead_source ON identified_profiles (lead_source)"),
    ("ix_identified_profiles_touchpoint_count",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_touchpoint_count ON identified_profiles (touchpoint_count DESC)"),
    ("ix_identified_profiles_last_interaction_at",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_last_interaction_at ON identified_profiles (last_interaction_at DESC)"),
    ("ix_identified_profiles_created_at",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_created_at ON identified_profiles (created_at DESC)"),
    ("ix_identified_profiles_is_fit",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_is_fit ON identified_profiles (id) WHERE is_fit = true"),
    ("ix_identified_profiles_is_competitor",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_is_competitor ON identified_profiles (id) WHERE is_competitor = true"),
    ("ix_identified_profiles_is_decision_maker",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_identified_profiles_is_decision_maker ON identified_profiles (id) WHERE is_decision_maker = true"),
    ("ix_research_reports_norm_url_created",
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_research_reports_norm_url_created ON research_reports (normalized_linkedin_url, created_at DESC)"),
]


def upgrade() -> None:
    # Get the raw DBAPI connection so we can control autocommit directly,
    # bypassing SQLAlchemy's transaction management entirely.
    bind = op.get_bind()
    raw_conn = bind.connection.dbapi_connection

    # psycopg2 requires no open transaction before changing autocommit.
    raw_conn.rollback()
    raw_conn.autocommit = True
    cur = raw_conn.cursor()
    cur.execute("SET statement_timeout = 0")

    # 1. Add lead_source column — IF NOT EXISTS guards against re-runs.
    cur.execute("""
        ALTER TABLE identified_profiles
        ADD COLUMN IF NOT EXISTS lead_source VARCHAR(50)
    """)

    # 2. Backfill lead_source from interaction_history in one pass.
    cur.execute("""
        UPDATE identified_profiles
        SET lead_source = CASE
            WHEN interaction_history ILIKE '%"competitor": "Apollo"%' THEN 'apollo'
            WHEN interaction_history ILIKE '%"competitor": "Keyword%'  THEN 'keyword'
            WHEN interaction_history IS NOT NULL AND interaction_history != '[]' THEN 'competitor'
            ELSE NULL
        END
        WHERE lead_source IS NULL
    """)

    # 3. Create indexes CONCURRENTLY — autocommit is already on, so each
    #    CREATE INDEX runs as its own implicit transaction (required for CONCURRENTLY).
    for _, ddl in CONCURRENT_INDEXES:
        cur.execute(ddl)

    cur.close()


def downgrade() -> None:
    bind = op.get_bind()
    raw_conn = bind.connection.dbapi_connection
    raw_conn.rollback()
    raw_conn.autocommit = True
    cur = raw_conn.cursor()
    cur.execute("SET statement_timeout = 0")

    for name, _ in CONCURRENT_INDEXES:
        cur.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")

    cur.execute("ALTER TABLE identified_profiles DROP COLUMN IF EXISTS lead_source")
    cur.close()
