"""plans table and firm chat usage tracking

Revision ID: 003
Revises: 002
Create Date: 2026-08-20

Adds:
  - plans table (subscription tiers with chat cap + pricing)
  - firms.plan_id FK → plans
  - firms.monthly_chats_used
  - firms.usage_reset_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "stl"


def upgrade() -> None:
    conn = op.get_bind()

    # ── plans table (IF NOT EXISTS) ───────────────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS "{SCHEMA}".plans (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name             TEXT NOT NULL UNIQUE,
            label            TEXT NOT NULL,
            monthly_chat_cap INTEGER NOT NULL,
            price_monthly    INTEGER NOT NULL,
            overage_per_chat INTEGER DEFAULT 15,
            created_at       TIMESTAMPTZ DEFAULT now()
        )
    """))

    # ── firms: add columns only if they don't exist ───────────────────────────
    for col_sql in [
        f'ALTER TABLE "{SCHEMA}".firms ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES "{SCHEMA}".plans(id)',
        f'ALTER TABLE "{SCHEMA}".firms ADD COLUMN IF NOT EXISTS monthly_chats_used INTEGER DEFAULT 0',
        f'ALTER TABLE "{SCHEMA}".firms ADD COLUMN IF NOT EXISTS usage_reset_at TIMESTAMPTZ DEFAULT now()',
    ]:
        conn.execute(sa.text(col_sql))


def downgrade() -> None:
    op.drop_constraint("fk_firms_plan_id", "firms", schema=SCHEMA, type_="foreignkey")
    op.drop_column("firms", "usage_reset_at", schema=SCHEMA)
    op.drop_column("firms", "monthly_chats_used", schema=SCHEMA)
    op.drop_column("firms", "plan_id", schema=SCHEMA)
    op.drop_table("plans", schema=SCHEMA)
