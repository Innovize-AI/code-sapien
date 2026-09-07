"""Add connected_accounts table for multi-account Gmail OAuth

Revision ID: 0005
Revises: 0004
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connected_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("token_json", sa.Text(), nullable=False),
        sa.Column("watch_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("history_id", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="rfq",
    )
    op.create_index("ix_connected_accounts_email", "connected_accounts", ["email"], schema="rfq")


def downgrade() -> None:
    op.drop_index("ix_connected_accounts_email", "connected_accounts", schema="rfq")
    op.drop_table("connected_accounts", schema="rfq")
