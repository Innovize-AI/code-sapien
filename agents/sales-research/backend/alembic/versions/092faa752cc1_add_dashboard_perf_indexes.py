"""Add composite indexes for dashboard query performance

Revision ID: 092faa752cc1
Revises: fc487ce6b28f
Create Date: 2026-06-29

Every dashboard query filters by (org/user, created_at) together.
Single-column indexes force the DB to intersect two index scans;
composite indexes satisfy the full predicate in one seek.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "092faa752cc1"
down_revision: Union[str, None] = "4773b71d36da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── identified_profiles ───────────────────────────────────────────────────
    # created_at range filter used in every analytics query
    op.create_index(
        "ix_identified_profiles_created_at",
        "identified_profiles", ["created_at"],
        postgresql_using="btree",
    )
    # Composite: org-scoped date-range (analytics + stats)
    op.create_index(
        "ix_identified_profiles_org_created_at",
        "identified_profiles", ["organization_id", "created_at"],
        postgresql_using="btree",
    )
    # Composite: user-scoped date-range (single-user mode)
    op.create_index(
        "ix_identified_profiles_user_created_at",
        "identified_profiles", ["created_by_id", "created_at"],
        postgresql_using="btree",
    )

    # ── research_reports ──────────────────────────────────────────────────────
    # created_at range filter used in reclassification query
    op.create_index(
        "ix_research_reports_created_at",
        "research_reports", ["created_at"],
        postgresql_using="btree",
    )
    # lead_score filtered > 70 in stats query
    op.create_index(
        "ix_research_reports_lead_score",
        "research_reports", ["lead_score"],
        postgresql_using="btree",
        postgresql_where=sa.text("lead_score IS NOT NULL"),
    )
    # Composite: org-scoped (stats + reclassification)
    op.create_index(
        "ix_research_reports_org_created_at",
        "research_reports", ["organization_id", "created_at"],
        postgresql_using="btree",
    )
    # Composite: user-scoped
    op.create_index(
        "ix_research_reports_user_created_at",
        "research_reports", ["created_by_id", "created_at"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_identified_profiles_created_at",      table_name="identified_profiles")
    op.drop_index("ix_identified_profiles_org_created_at",  table_name="identified_profiles")
    op.drop_index("ix_identified_profiles_user_created_at", table_name="identified_profiles")
    op.drop_index("ix_research_reports_created_at",         table_name="research_reports")
    op.drop_index("ix_research_reports_lead_score",         table_name="research_reports")
    op.drop_index("ix_research_reports_org_created_at",     table_name="research_reports")
    op.drop_index("ix_research_reports_user_created_at",    table_name="research_reports")
