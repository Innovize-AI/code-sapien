"""initial rfq_submissions table

Revision ID: 0001
Revises:
Create Date: 2026-07-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rfq_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rfq_id", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.text("now()")),

        # Intake
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("sender", sa.String(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),

        # Buyer info
        sa.Column("buyer_name", sa.Text(), nullable=True),
        sa.Column("buyer_contact", sa.Text(), nullable=True),
        sa.Column("delivery_location", sa.Text(), nullable=True),
        sa.Column("rfq_deadline", sa.Text(), nullable=True),

        # Classification
        sa.Column("urgency", sa.String(), nullable=True),
        sa.Column("complexity", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),

        # Parsed data (JSONB)
        sa.Column("line_items", JSONB(), nullable=True),
        sa.Column("catalog_matches", JSONB(), nullable=True),
        sa.Column("feasibility", JSONB(), nullable=True),
        sa.Column("unfulfillable_items", JSONB(), nullable=True),

        # Pricing
        sa.Column("line_pricing", JSONB(), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("pricing_confidence", sa.Float(), nullable=True),

        # Output
        sa.Column("draft_quote", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),

        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="processing"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )

    # Indexes for common queries
    op.create_index("ix_rfq_submissions_status", "rfq_submissions", ["status"])
    op.create_index("ix_rfq_submissions_sender", "rfq_submissions", ["sender"])
    op.create_index("ix_rfq_submissions_created_at", "rfq_submissions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_rfq_submissions_created_at", table_name="rfq_submissions")
    op.drop_index("ix_rfq_submissions_sender", table_name="rfq_submissions")
    op.drop_index("ix_rfq_submissions_status", table_name="rfq_submissions")
    op.drop_table("rfq_submissions")
