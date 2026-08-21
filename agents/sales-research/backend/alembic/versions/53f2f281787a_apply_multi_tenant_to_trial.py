"""apply_multi_tenant_to_trial

Revision ID: 53f2f281787a
Revises: b3f1a2c9d4e5
Create Date: 2026-04-22 17:42:32.707876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision: str = '53f2f281787a'
down_revision: Union[str, Sequence[str], None] = 'b3f1a2c9d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def safe_drop_index(index_name, table_name):
    op.execute(f'DROP INDEX IF EXISTS {index_name}')

def safe_create_index(index_name, table_name, columns, unique=False, postgresql_where=None):
    unique_str = "UNIQUE" if unique else ""
    cols_str = ", ".join(columns)
    where_str = f"WHERE {postgresql_where}" if postgresql_where else ""
    op.execute(f'CREATE {unique_str} INDEX IF NOT EXISTS {index_name} ON {table_name} ({cols_str}) {where_str}')

def safe_add_column(table_name, column_name, column_type):
    # Postgres doesn't have ADD COLUMN IF NOT EXISTS in old versions, but 9.6+ does
    op.execute(f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}')

def safe_drop_column(table_name, column_name):
    op.execute(f'ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}')

def safe_drop_constraint(constraint_name, table_name):
    op.execute(f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}')

def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create Organizations table safely
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ
        )
    """)

    # 2. Update Activities
    safe_add_column('activities', 'organization_id', 'UUID')
    safe_drop_index('ix_staging_activities_company_id', 'activities')
    safe_create_index('ix_activities_company_id', 'activities', ['company_id'])
    safe_create_index('ix_activities_organization_id', 'activities', ['organization_id'])
    safe_drop_constraint('fk_activities_company_id_companies', 'activities')

    # 3. Update Companies
    safe_drop_constraint('companies_domain_key', 'companies')
    safe_drop_constraint('companies_linkedin_url_key', 'companies')
    safe_drop_index('ix_staging_companies_apollo_id', 'companies')
    safe_create_index('ix_companies_apollo_id', 'companies', ['apollo_id'])
    safe_create_index('ix_companies_domain', 'companies', ['domain'], unique=True)
    safe_create_index('ix_companies_linkedin_url', 'companies', ['linkedin_url'], unique=True)
    safe_drop_column('companies', 'email')

    # 4. Update Competitor Analysis
    safe_add_column('competitor_analysis', 'organization_id', 'UUID')
    safe_create_index('ix_competitor_analysis_organization_id', 'competitor_analysis', ['organization_id'])
    
    # 5. Update Competitors
    safe_add_column('competitors', 'organization_id', 'UUID')
    safe_create_index('ix_competitors_organization_id', 'competitors', ['organization_id'])

    # 6. Update CRM Context
    safe_drop_index('ix_crm_context_email', 'crm_context')
    safe_drop_index('ix_crm_context_linkedin_url', 'crm_context')
    safe_create_index('ix_crm_context_email', 'crm_context', ['email'])
    safe_create_index('ix_crm_context_linkedin_url', 'crm_context', ['linkedin_url'])

    # 7. Update Identified Profiles
    safe_add_column('identified_profiles', 'organization_id', 'UUID')
    safe_drop_index('ix_identified_profiles_created_at', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_is_competitor', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_is_decision_maker', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_is_fit', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_last_interaction_at', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_lead_source', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_normalized_linkedin_url', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_touchpoint_count', 'identified_profiles')
    safe_drop_index('ix_staging_identified_profiles_company_id', 'identified_profiles')
    
    safe_create_index('ix_identified_profiles_company_id', 'identified_profiles', ['company_id'])
    safe_create_index('ix_identified_profiles_lead_source', 'identified_profiles', ['lead_source'])
    safe_create_index('ix_identified_profiles_normalized_linkedin_url', 'identified_profiles', ['normalized_linkedin_url'])
    safe_create_index('ix_identified_profiles_organization_id', 'identified_profiles', ['organization_id'])
    safe_drop_constraint('fk_identified_profiles_company_id_companies', 'identified_profiles')

    # 8. Update Lead Submissions
    safe_add_column('lead_submissions', 'organization_id', 'UUID')
    safe_add_column('lead_submissions', 'created_by_id', 'UUID')
    safe_create_index('ix_lead_submissions_created_by_id', 'lead_submissions', ['created_by_id'])
    safe_create_index('ix_lead_submissions_organization_id', 'lead_submissions', ['organization_id'])

    # 9. Update Organization Settings
    safe_add_column('organization_settings', 'organization_id', 'UUID')
    safe_add_column('organization_settings', 'owner_id', 'UUID')
    safe_add_column('organization_settings', 'pinecone_index_name', 'TEXT')
    safe_create_index('ix_organization_settings_organization_id', 'organization_settings', ['organization_id'])
    safe_create_index('ix_organization_settings_owner_id', 'organization_settings', ['owner_id'])

    # 10. Update Research Reports
    safe_add_column('research_reports', 'organization_id', 'UUID')
    safe_drop_index('ix_research_reports_norm_url_created', 'research_reports')
    safe_drop_index('ix_research_reports_normalized_linkedin_url', 'research_reports')
    safe_drop_index('ix_staging_research_reports_company_id', 'research_reports')
    
    safe_create_index('ix_research_reports_company_id', 'research_reports', ['company_id'])
    safe_create_index('ix_research_reports_normalized_linkedin_url', 'research_reports', ['normalized_linkedin_url'])
    safe_create_index('ix_research_reports_organization_id', 'research_reports', ['organization_id'])
    safe_drop_constraint('fk_research_reports_company_id_companies', 'research_reports')

    # 11. Update User Settings
    safe_add_column('user_settings', 'organization_id', 'UUID')
    safe_create_index('ix_user_settings_organization_id', 'user_settings', ['organization_id'])

def downgrade() -> None:
    """Downgrade schema."""
    safe_drop_index('ix_user_settings_organization_id', 'user_settings')
    safe_drop_column('user_settings', 'organization_id')
    
    safe_drop_index('ix_research_reports_organization_id', 'research_reports')
    safe_drop_index('ix_research_reports_normalized_linkedin_url', 'research_reports')
    safe_drop_index('ix_research_reports_company_id', 'research_reports')
    
    safe_create_index('ix_staging_research_reports_company_id', 'research_reports', ['company_id'])
    safe_create_index('ix_research_reports_normalized_linkedin_url', 'research_reports', ['normalized_linkedin_url'])
    safe_drop_column('research_reports', 'organization_id')
    
    safe_drop_index('ix_organization_settings_owner_id', 'organization_settings')
    safe_drop_index('ix_organization_settings_organization_id', 'organization_settings')
    safe_drop_column('organization_settings', 'pinecone_index_name')
    safe_drop_column('organization_settings', 'owner_id')
    safe_drop_column('organization_settings', 'organization_id')
    
    safe_drop_index('ix_lead_submissions_organization_id', 'lead_submissions')
    safe_drop_index('ix_lead_submissions_created_by_id', 'lead_submissions')
    safe_drop_column('lead_submissions', 'created_by_id')
    safe_drop_column('lead_submissions', 'organization_id')
    
    safe_drop_index('ix_identified_profiles_organization_id', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_normalized_linkedin_url', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_lead_source', 'identified_profiles')
    safe_drop_index('ix_identified_profiles_company_id', 'identified_profiles')
    
    safe_create_index('ix_staging_identified_profiles_company_id', 'identified_profiles', ['company_id'])
    safe_create_index('ix_identified_profiles_touchpoint_count', 'identified_profiles', ['touchpoint_count'])
    safe_create_index('ix_identified_profiles_normalized_linkedin_url', 'identified_profiles', ['normalized_linkedin_url'])
    safe_create_index('ix_identified_profiles_lead_source', 'identified_profiles', ['lead_source'])
    safe_create_index('ix_identified_profiles_last_interaction_at', 'identified_profiles', ['last_interaction_at'])
    safe_create_index('ix_identified_profiles_created_at', 'identified_profiles', ['created_at'])
    safe_drop_column('identified_profiles', 'organization_id')
    
    safe_drop_index('ix_crm_context_linkedin_url', 'crm_context')
    safe_drop_index('ix_crm_context_email', 'crm_context')
    safe_create_index('ix_crm_context_linkedin_url', 'crm_context', ['linkedin_url'])
    safe_create_index('ix_crm_context_email', 'crm_context', ['email'])
    
    safe_drop_index('ix_competitors_organization_id', 'competitors')
    safe_drop_column('competitors', 'organization_id')
    safe_drop_index('ix_competitor_analysis_organization_id', 'competitor_analysis')
    safe_drop_column('competitor_analysis', 'organization_id')
    
    safe_drop_index('ix_activities_organization_id', 'activities')
    safe_drop_index('ix_activities_company_id', 'activities')
    safe_create_index('ix_staging_activities_company_id', 'activities', ['company_id'])
    safe_drop_column('activities', 'organization_id')
    
    op.execute('DROP TABLE IF EXISTS organizations')
