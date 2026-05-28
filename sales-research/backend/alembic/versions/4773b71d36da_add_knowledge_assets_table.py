"""add_knowledge_assets_table

Revision ID: 4773b71d36da
Revises: 70e9558e0cc6
Create Date: 2026-04-29 17:22:04.451572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '4773b71d36da'
down_revision: Union[str, Sequence[str], None] = '70e9558e0cc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'knowledge_assets',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('namespace', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('asset_metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_assets_organization_id', 'knowledge_assets', ['organization_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_knowledge_assets_organization_id', table_name='knowledge_assets')
    op.drop_table('knowledge_assets')
