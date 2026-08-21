"""sync_models_with_migrations

Revision ID: f4ea93766723
Revises: 2e8a57a02ac1
Create Date: 2026-02-24 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4ea93766723'
down_revision: Union[str, Sequence[str], None] = '2e8a57a02ac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # --- research_reports ---
    rr_columns = [c['name'] for c in inspector.get_columns('research_reports')]
    
    # Missing Columns from Audit
    missing_rr = [
        ('company_name', sa.Text()),
        ('company_description', sa.Text()),
        ('company_industries', sa.Text()),
        ('company_stats', sa.Text()),
        ('viability_analysis', sa.Text()),
        ('target_pain_points', sa.Text()),
        ('strategic_solutions', sa.Text()),
        ('personalized_outreach', sa.Text()),
        ('follow_up_strategy', sa.Text()),
        ('buyer_journey_analysis', sa.Text()),
        ('meeting_notes', sa.Text()),
        ('post_engagements', sa.Text()),
        ('company_news', sa.Text()),
        ('hiring_data', sa.Text()),
        ('icp_context', sa.Text()),
        ('email_history', sa.Text()),
        ('intent_analysis', sa.Text()),
    ]
    
    for col_name, col_type in missing_rr:
        if col_name not in rr_columns:
            op.add_column('research_reports', sa.Column(col_name, col_type, nullable=True))

    # --- lead_submissions ---
    if 'lead_submissions' in inspector.get_table_names():
        ls_columns = [c['name'] for c in inspector.get_columns('lead_submissions')]
        missing_ls = [
            ('email_history', sa.Text()),
            ('intent_analysis', sa.Text()),
            ('extra_metadata', sa.Text()),
        ]
        for col_name, col_type in missing_ls:
            if col_name not in ls_columns:
                op.add_column('lead_submissions', sa.Column(col_name, col_type, nullable=True))

    # --- organization_settings ---
    os_columns = [c['name'] for c in inspector.get_columns('organization_settings')]
    missing_os = [
        ('user_linkedin_url', sa.Text()),
        ('company_linkedin_url', sa.Text()),
        ('integrations_config', sa.Text()),
    ]
    for col_name, col_type in missing_os:
        if col_name not in os_columns:
            op.add_column('organization_settings', sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    # Downgrades for added columns (optional in sync migrations but good practice)
    # Note: We only drop what was added in upgrade, but since it's a sync migration, we omit for safety
    pass
