"""add slack integration and activities

Revision ID: a38f5a96beb1
Revises: 90f4512788a3
Create Date: 2026-02-09 13:33:16.871062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38f5a96beb1'
down_revision: Union[str, Sequence[str], None] = '90f4512788a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add slack_webhook_url to organization_settings
    op.add_column('organization_settings', sa.Column('slack_webhook_url', sa.String(), nullable=True))
    
    # Create activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('activities')
    op.drop_column('organization_settings', 'slack_webhook_url')
