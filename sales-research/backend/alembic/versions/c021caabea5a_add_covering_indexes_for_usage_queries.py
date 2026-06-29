"""Add covering indexes for usage/stats aggregate queries

Revision ID: c021caabea5a
Revises: 092faa752cc1
Create Date: 2026-06-29

The stats and usage endpoints run:
  SELECT COUNT(*), AVG(lead_score), COUNT(*) FILTER (WHERE lead_score > 70)
  FROM research_reports WHERE organization_id = $1

Without a covering index, PostgreSQL finds the rows via the org index then
fetches each heap page to read lead_score — slow on large tables.
With (organization_id, lead_score), the query is satisfied from the index alone.

Same pattern for identified_profiles classification counts.
"""
from typing import Sequence, Union
from alembic import op


revision: str = "c021caabea5a"
down_revision: Union[str, None] = "092faa752cc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Covering index: allows index-only scan for COUNT + AVG(lead_score)
    op.create_index(
        "ix_research_reports_org_score",
        "research_reports", ["organization_id", "lead_score"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_research_reports_user_score",
        "research_reports", ["created_by_id", "lead_score"],
        postgresql_using="btree",
    )
    # Covering index for classification count: COUNT WHERE is_fit OR intent IS NOT NULL
    op.create_index(
        "ix_identified_profiles_org_fit_intent",
        "identified_profiles", ["organization_id", "is_fit", "intent"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_identified_profiles_user_fit_intent",
        "identified_profiles", ["created_by_id", "is_fit", "intent"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_research_reports_org_score",          table_name="research_reports")
    op.drop_index("ix_research_reports_user_score",         table_name="research_reports")
    op.drop_index("ix_identified_profiles_org_fit_intent",  table_name="identified_profiles")
    op.drop_index("ix_identified_profiles_user_fit_intent", table_name="identified_profiles")
