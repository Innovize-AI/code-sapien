"""merge heads

Revision ID: 90f4512788a3
Revises: 2c20b9318e35, 30a0caff4445
Create Date: 2026-02-09 13:33:10.164911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90f4512788a3'
down_revision: Union[str, Sequence[str], None] = ('2c20b9318e35', '30a0caff4445')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
