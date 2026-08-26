"""add_copilot_chat_logs_table

Revision ID: 1a5f19287ea2
Revises: c021caabea5a
Create Date: 2026-08-21 20:19:51.291194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a5f19287ea2'
down_revision: Union[str, Sequence[str], None] = 'c021caabea5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    
    # Create copilot_chat_logs table if not exists (check first)
    op.create_table(
        'copilot_chat_logs',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('report_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(length=50), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sources', sa.dialects.postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['research_reports.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_copilot_chat_logs_report_id'), 'copilot_chat_logs', ['report_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_copilot_chat_logs_report_id'), table_name='copilot_chat_logs')
    op.drop_table('copilot_chat_logs')
