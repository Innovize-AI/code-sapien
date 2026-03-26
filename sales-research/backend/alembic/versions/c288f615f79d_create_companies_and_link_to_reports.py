"""create companies and link to reports

Revision ID: c288f615f79d
Revises: 09da1a1c1f75
Create Date: 2026-03-19 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c288f615f79d'
down_revision: Union[str, Sequence[str], None] = '09da1a1c1f75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create Companies Table
    op.create_table('companies',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('linkedin_url', sa.Text(), nullable=True),
        sa.Column('website', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industries', sa.Text(), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('revenue', sa.Text(), nullable=True),
        sa.Column('market_cap', sa.Text(), nullable=True),
        sa.Column('total_funding', sa.Text(), nullable=True),
        sa.Column('headquarters', sa.Text(), nullable=True),
        sa.Column('follower_count', sa.Integer(), nullable=True),
        sa.Column('employee_count_range', sa.Text(), nullable=True),
        sa.Column('news', sa.Text(), nullable=True),
        sa.Column('hiring', sa.Text(), nullable=True),
        sa.Column('technologies', sa.Text(), nullable=True),
        sa.Column('technology_names', sa.Text(), nullable=True),
        sa.Column('funding_events', sa.Text(), nullable=True),
        sa.Column('latest_funding_stage', sa.Text(), nullable=True),
        sa.Column('latest_funding_date', sa.Text(), nullable=True),
        sa.Column('headcount_growth', sa.Text(), nullable=True),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('apollo_id', sa.String(), nullable=True),
        sa.Column('extra_metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
        sa.UniqueConstraint('linkedin_url')
    )
    op.create_index(op.f('ix_staging_companies_apollo_id'), 'companies', ['apollo_id'], unique=False)

    # 2. Add company_id to research_reports
    op.add_column('research_reports', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_research_reports_company_id_companies', 'research_reports', 'companies', ['company_id'], ['id'])
    op.create_index(op.f('ix_staging_research_reports_company_id'), 'research_reports', ['company_id'], unique=False)

    # 3. Add company_id and missing email to identified_profiles
    op.add_column('identified_profiles', sa.Column('email', sa.String(), nullable=True))
    op.add_column('identified_profiles', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_identified_profiles_company_id_companies', 'identified_profiles', 'companies', ['company_id'], ['id'])
    op.create_index(op.f('ix_staging_identified_profiles_company_id'), 'identified_profiles', ['company_id'], unique=False)

    # 4. Add company_id to activities
    op.add_column('activities', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_activities_company_id_companies', 'activities', 'companies', ['company_id'], ['id'])
    op.create_index(op.f('ix_staging_activities_company_id'), 'activities', ['company_id'], unique=False)

def downgrade() -> None:
    op.drop_constraint('fk_activities_company_id_companies', 'activities', type_='foreignkey')
    op.drop_index(op.f('ix_staging_activities_company_id'), table_name='activities')
    op.drop_column('activities', 'company_id')

    op.drop_constraint('fk_identified_profiles_company_id_companies', 'identified_profiles', type_='foreignkey')
    op.drop_index(op.f('ix_staging_identified_profiles_company_id'), table_name='identified_profiles')
    op.drop_column('identified_profiles', 'company_id')
    op.drop_column('identified_profiles', 'email')

    op.drop_constraint('fk_research_reports_company_id_companies', 'research_reports', type_='foreignkey')
    op.drop_index(op.f('ix_staging_research_reports_company_id'), table_name='research_reports')
    op.drop_column('research_reports', 'company_id')

    op.drop_table('companies')
