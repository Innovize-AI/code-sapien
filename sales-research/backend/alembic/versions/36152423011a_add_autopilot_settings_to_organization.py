"""add autopilot settings to organization

Revision ID: 36152423011a
Revises: f9d9aa1f52db
Create Date: 2026-02-18 11:03:12.587134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36152423011a'
down_revision: Union[str, Sequence[str], None] = 'f9d9aa1f52db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organization_settings', sa.Column('discovery_keywords', sa.Text(), nullable=True))
    op.add_column('organization_settings', sa.Column('apollo_search_config', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organization_settings', 'apollo_search_config')
    op.drop_column('organization_settings', 'discovery_keywords')

