"""add_idempotency_key_to_activities

Revision ID: 9c3904efb4bc
Revises: 9fd24d0c50fd
Create Date: 2026-02-28 12:38:25.873197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c3904efb4bc'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the column to the activities table
    op.add_column('activities', sa.Column('idempotency_key', sa.String(), nullable=True))
    # Create the unique constraint
    op.create_unique_constraint('idx_activities_idempotency_key', 'activities', ['idempotency_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('idx_activities_idempotency_key', 'activities', type_='unique')
    op.drop_column('activities', 'idempotency_key')
