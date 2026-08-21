"""add normalized linkedin url columns

Revision ID: c2cc289a6061
Revises: c288f615f79d
Create Date: 2026-03-20 14:10:04.971357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2cc289a6061'
down_revision: Union[str, Sequence[str], None] = 'c288f615f79d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns
    op.add_column('research_reports', sa.Column('normalized_linkedin_url', sa.Text(), nullable=True))
    op.add_column('identified_profiles', sa.Column('normalized_linkedin_url', sa.Text(), nullable=True))
    
    # Add indices
    op.create_index('ix_research_reports_normalized_linkedin_url', 'research_reports', ['normalized_linkedin_url'], unique=False)
    op.create_index('ix_identified_profiles_normalized_linkedin_url', 'identified_profiles', ['normalized_linkedin_url'], unique=False)


def downgrade() -> None:
    # Drop indices
    op.drop_index('ix_identified_profiles_normalized_linkedin_url', table_name='identified_profiles')
    op.drop_index('ix_research_reports_normalized_linkedin_url', table_name='research_reports')
    
    # Drop columns
    op.drop_column('identified_profiles', 'normalized_linkedin_url')
    op.drop_column('research_reports', 'normalized_linkedin_url')
