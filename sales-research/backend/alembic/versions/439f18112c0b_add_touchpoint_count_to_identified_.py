"""add touchpoint_count to identified_profiles

Revision ID: 439f18112c0b
Revises: 885a7d2efdeb
Create Date: 2026-03-04 17:13:43.417408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '439f18112c0b'
down_revision: Union[str, Sequence[str], None] = '885a7d2efdeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('identified_profiles', sa.Column('touchpoint_count', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('identified_profiles', 'touchpoint_count')
