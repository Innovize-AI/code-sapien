"""final_robust_schema_sync

Revision ID: a1b2c3d4e5f6
Revises: f4ea93766723
Create Date: 2026-02-24 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4ea93766723'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- research_reports ---
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS fullname TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS profile_picture_url TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS company_name TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS company_description TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS company_industries TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS company_stats TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS viability_analysis TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS target_pain_points TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS strategic_solutions TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS personalized_outreach TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS follow_up_strategy TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS buyer_journey_analysis TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS meeting_notes TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS post_engagements TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS company_news TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS hiring_data TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS lead_company_linkedin_url TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS lead_li_urn TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS created_by_id UUID')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS icp_context TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS email_history TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS intent_analysis TEXT')
    op.execute('ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS extra_metadata TEXT')

    # --- lead_submissions ---
    # Ensure table exists first (it should, but safety first in sync migrations)
    op.execute("DO $$ BEGIN IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_submissions') THEN "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS action_type TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS action_metadata TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS external_form_id TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS external_form_name TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS research_id UUID; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS rep_id UUID; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS email_history TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS intent_analysis TEXT; "
               "ALTER TABLE lead_submissions ADD COLUMN IF NOT EXISTS extra_metadata TEXT; "
               "END IF; END $$;")

    # --- organization_settings ---
    op.execute('ALTER TABLE organization_settings ADD COLUMN IF NOT EXISTS user_linkedin_url TEXT')
    op.execute('ALTER TABLE organization_settings ADD COLUMN IF NOT EXISTS company_linkedin_url TEXT')
    op.execute('ALTER TABLE organization_settings ADD COLUMN IF NOT EXISTS integrations_config TEXT')


def downgrade() -> None:
    pass
