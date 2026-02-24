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
    
    # Check research_reports columns
    rr_columns = [c['name'] for c in inspector.get_columns('research_reports')]
    
    if 'company_name' not in rr_columns:
        op.add_column('research_reports', sa.Column('company_name', sa.Text(), nullable=True))
    if 'company_description' not in rr_columns:
        op.add_column('research_reports', sa.Column('company_description', sa.Text(), nullable=True))
    if 'company_industries' not in rr_columns:
        op.add_column('research_reports', sa.Column('company_industries', sa.Text(), nullable=True))
    if 'post_engagements' not in rr_columns:
        op.add_column('research_reports', sa.Column('post_engagements', sa.Text(), nullable=True))
    if 'company_news' not in rr_columns:
        op.add_column('research_reports', sa.Column('company_news', sa.Text(), nullable=True))
    if 'hiring_data' not in rr_columns:
        op.add_column('research_reports', sa.Column('hiring_data', sa.Text(), nullable=True))

    # Check organization_settings columns
    os_columns = [c['name'] for c in inspector.get_columns('organization_settings')]
    
    if 'user_linkedin_url' not in os_columns:
        op.add_column('organization_settings', sa.Column('user_linkedin_url', sa.Text(), nullable=True))
    if 'company_linkedin_url' not in os_columns:
        op.add_column('organization_settings', sa.Column('company_linkedin_url', sa.Text(), nullable=True))
    if 'integrations_config' not in os_columns:
        op.add_column('organization_settings', sa.Column('integrations_config', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from organization_settings
    op.drop_column('organization_settings', 'integrations_config')
    op.drop_column('organization_settings', 'company_linkedin_url')
    op.drop_column('organization_settings', 'user_linkedin_url')

    # Remove columns from research_reports
    op.drop_column('research_reports', 'hiring_data')
    op.drop_column('research_reports', 'company_news')
    op.drop_column('research_reports', 'post_engagements')
    op.drop_column('research_reports', 'company_industries')
    op.drop_column('research_reports', 'company_description')
    op.drop_column('research_reports', 'company_name')
