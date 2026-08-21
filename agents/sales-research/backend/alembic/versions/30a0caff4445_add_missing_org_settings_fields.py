"""add missing org settings fields

Revision ID: 30a0caff4445
Revises: 072e7c3d35e1
Create Date: 2026-02-09 13:04:45.918261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30a0caff4445'
down_revision: Union[str, Sequence[str], None] = '072e7c3d35e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organization_settings', sa.Column('onboarding_complete', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('organization_settings', sa.Column('kit_api_key', sa.String(), nullable=True))
    # op.add_column('organization_settings', sa.Column('kit_api_secret', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organization_settings', 'kit_api_secret')
    op.drop_column('organization_settings', 'kit_api_key')
    op.drop_column('organization_settings', 'onboarding_complete')
    op.drop_column('organization_settings', 'integrations_config')
