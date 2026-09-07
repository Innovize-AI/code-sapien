"""Add document_type column to rfq_submissions

Revision ID: 0004
Revises: 0003
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rfq_submissions",
        sa.Column("document_type", sa.String(), nullable=True, server_default="RFQ"),
        schema="rfq",
    )


def downgrade() -> None:
    op.drop_column("rfq_submissions", "document_type", schema="rfq")
