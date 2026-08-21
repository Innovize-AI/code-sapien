"""add sorting indices to identified profiles

Revision ID: 2c9df31836a9
Revises: c2cc289a6061
Create Date: 2026-03-20 14:16:46.958567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c9df31836a9'
down_revision: Union[str, Sequence[str], None] = 'c2cc289a6061'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indices for common sort columns
    op.create_index('ix_identified_profiles_touchpoint_count', 'identified_profiles', ['touchpoint_count'], unique=False)
    op.create_index('ix_identified_profiles_last_interaction_at', 'identified_profiles', ['last_interaction_at'], unique=False)


def downgrade() -> None:
    # Drop indices
    op.drop_index('ix_identified_profiles_last_interaction_at', table_name='identified_profiles')
    op.drop_index('ix_identified_profiles_touchpoint_count', table_name='identified_profiles')
