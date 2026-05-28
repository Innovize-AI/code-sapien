"""add_cascade_to_trial_org_settings

Revision ID: 073d63790902
Revises: b7db066ccea0
Create Date: 2026-04-23 17:58:20.966581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '073d63790902'
down_revision: Union[str, Sequence[str], None] = 'b7db066ccea0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 0. Cleanup orphaned settings that would violate the FK
    op.execute(f'DELETE FROM organization_settings WHERE organization_id NOT IN (SELECT id FROM organizations) AND organization_id IS NOT NULL')
    
    # 1. Drop existing FK if it exists
    op.execute(f'ALTER TABLE organization_settings DROP CONSTRAINT IF EXISTS organization_settings_organization_id_fkey')
    
    # 2. Add it back with CASCADE
    op.create_foreign_key(
        'organization_settings_organization_id_fkey',
        'organization_settings',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove CASCADE and put back a normal FK
    op.drop_constraint('organization_settings_organization_id_fkey', 'organization_settings', type_='foreignkey')
    op.create_foreign_key(
        'organization_settings_organization_id_fkey',
        'organization_settings',
        'organizations',
        ['organization_id'],
        ['id']
    )
