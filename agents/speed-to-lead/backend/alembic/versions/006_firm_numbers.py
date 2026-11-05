"""firm_numbers: several WhatsApp numbers per firm, each attached to a person

Revision ID: 006
Revises: 005
Create Date: 2026-11-05

Additive and idempotent. Adds:
  - firm_numbers
  - brokers.kind (partner | team) and brokers.email
  - leads.number_id and leads.owner_id
  - conversation_logs.number_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "stl"


def upgrade() -> None:
    conn = op.get_bind()
    for sql in [
        f"""CREATE TABLE IF NOT EXISTS "{SCHEMA}".firm_numbers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES "{SCHEMA}".firms(id),
            person_id UUID REFERENCES "{SCHEMA}".brokers(id) ON DELETE SET NULL,
            label TEXT NOT NULL,
            display_phone TEXT,
            wa_phone_number_id TEXT NOT NULL UNIQUE,
            meta_access_token TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
        f'CREATE INDEX IF NOT EXISTS ix_firm_numbers_firm ON "{SCHEMA}".firm_numbers(firm_id)',
        f'CREATE INDEX IF NOT EXISTS ix_firm_numbers_person ON "{SCHEMA}".firm_numbers(person_id)',
        f"ALTER TABLE \"{SCHEMA}\".brokers ADD COLUMN IF NOT EXISTS kind TEXT DEFAULT 'partner'",
        f'ALTER TABLE "{SCHEMA}".brokers ADD COLUMN IF NOT EXISTS email TEXT',
        f'ALTER TABLE "{SCHEMA}".leads ADD COLUMN IF NOT EXISTS number_id UUID REFERENCES "{SCHEMA}".firm_numbers(id) ON DELETE SET NULL',
        f'ALTER TABLE "{SCHEMA}".leads ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES "{SCHEMA}".brokers(id) ON DELETE SET NULL',
        f'CREATE INDEX IF NOT EXISTS ix_leads_owner ON "{SCHEMA}".leads(owner_id)',
        f'CREATE INDEX IF NOT EXISTS ix_leads_number ON "{SCHEMA}".leads(number_id)',
        f'ALTER TABLE "{SCHEMA}".conversation_logs ADD COLUMN IF NOT EXISTS number_id UUID REFERENCES "{SCHEMA}".firm_numbers(id) ON DELETE SET NULL',
        f'CREATE INDEX IF NOT EXISTS ix_logs_number ON "{SCHEMA}".conversation_logs(number_id)',
    ]:
        conn.execute(sa.text(sql))


def downgrade() -> None:
    conn = op.get_bind()
    for sql in [
        f'ALTER TABLE "{SCHEMA}".conversation_logs DROP COLUMN IF EXISTS number_id',
        f'ALTER TABLE "{SCHEMA}".leads DROP COLUMN IF EXISTS number_id',
        f'ALTER TABLE "{SCHEMA}".leads DROP COLUMN IF EXISTS owner_id',
        f'ALTER TABLE "{SCHEMA}".brokers DROP COLUMN IF EXISTS kind',
        f'ALTER TABLE "{SCHEMA}".brokers DROP COLUMN IF EXISTS email',
        f'DROP TABLE IF EXISTS "{SCHEMA}".firm_numbers',
    ]:
        conn.execute(sa.text(sql))
