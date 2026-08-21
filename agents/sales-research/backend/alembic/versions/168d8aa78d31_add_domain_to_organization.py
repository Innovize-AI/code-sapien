"""add_domain_to_organization

Revision ID: 168d8aa78d31
Revises: 073d63790902
Create Date: 2026-04-28 21:55:15.281080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '168d8aa78d31'
down_revision: Union[str, Sequence[str], None] = '073d63790902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organizations', sa.Column('domain', sa.String(), nullable=True))
    op.create_index(op.f('ix_organizations_domain'), 'organizations', ['domain'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_organizations_domain'), table_name='organizations')
    op.drop_column('organizations', 'domain')
