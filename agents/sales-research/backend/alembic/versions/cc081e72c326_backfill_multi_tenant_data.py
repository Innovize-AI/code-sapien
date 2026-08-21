"""Backfill multi-tenant data

Revision ID: cc081e72c326
Revises: ddc58505201b
Create Date: 2026-02-17 13:25:27.832304

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc081e72c326'
down_revision: Union[str, Sequence[str], None] = 'ddc58505201b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
