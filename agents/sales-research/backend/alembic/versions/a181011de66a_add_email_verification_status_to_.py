"""add email_verification_status to identified_profile

Revision ID: a181011de66a
Revises: 2c9df31836a9
Create Date: 2026-04-05 18:28:17.108939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a181011de66a'
down_revision: Union[str, Sequence[str], None] = '2c9df31836a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('organization_settings')]
    
    # 1. Drop the legacy column if it exists (refactoring to JSON)
    if 'million_verifier_enabled' in columns:
        op.drop_column('organization_settings', 'million_verifier_enabled')
    
    # 2. Add new columns
    op.add_column('identified_profiles', sa.Column('email_verification_status', sa.String(), nullable=True))
    op.add_column('organization_settings', sa.Column('million_verifier_api_key', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organization_settings', 'million_verifier_api_key')
    op.drop_column('identified_profiles', 'email_verification_status')
