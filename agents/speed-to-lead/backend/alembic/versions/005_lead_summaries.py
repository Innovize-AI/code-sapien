"""lead_summaries: cached AI conversation summaries

Revision ID: 005
Revises: 004
Create Date: 2026-11-04

Additive and idempotent.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "stl"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS "{SCHEMA}".lead_summaries (
            lead_id UUID PRIMARY KEY REFERENCES "{SCHEMA}".leads(id) ON DELETE CASCADE,
            summary JSONB NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            model TEXT,
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))


def downgrade() -> None:
    op.get_bind().execute(sa.text(f'DROP TABLE IF EXISTS "{SCHEMA}".lead_summaries'))
