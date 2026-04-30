"""add_org_id_to_profile

Revision ID: b7db066ccea0
Revises: 53f2f281787a
Create Date: 2026-04-22 18:32:23.601569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7db066ccea0'
down_revision: Union[str, Sequence[str], None] = '53f2f281787a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS organization_id UUID')
    op.execute('CREATE INDEX IF NOT EXISTS ix_profiles_organization_id ON profiles (organization_id)')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP INDEX IF EXISTS ix_profiles_organization_id')
    op.execute('ALTER TABLE profiles DROP COLUMN IF EXISTS organization_id')
