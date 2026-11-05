"""broker registry: projects, brokers, lead_registrations, lead attribution

Revision ID: 004
Revises: 003
Create Date: 2026-11-04

Additive and idempotent. Adds:
  - projects (RERA number, possession, price facts, broker registration validity)
  - brokers (channel partners, identity = personal WhatsApp number, coded link)
  - lead_registrations (timestamped ownership ledger with conflict tracking)
  - leads.broker_id, leads.project_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "stl"


def upgrade() -> None:
    conn = op.get_bind()
    stmts = [
        # firms.contact_phone / contact_email are in the model but were never migrated
        f'ALTER TABLE "{SCHEMA}".firms ADD COLUMN IF NOT EXISTS contact_phone TEXT',
        f'ALTER TABLE "{SCHEMA}".firms ADD COLUMN IF NOT EXISTS contact_email TEXT',
        f"""CREATE TABLE IF NOT EXISTS "{SCHEMA}".projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES "{SCHEMA}".firms(id),
            name TEXT NOT NULL,
            location TEXT,
            rera_number TEXT,
            possession_date DATE,
            starting_price TEXT,
            payment_plan TEXT,
            bank_tieups TEXT,
            validity_days INTEGER DEFAULT 60,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
        f'CREATE INDEX IF NOT EXISTS ix_projects_firm ON "{SCHEMA}".projects(firm_id)',
        f"""CREATE TABLE IF NOT EXISTS "{SCHEMA}".brokers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES "{SCHEMA}".firms(id),
            name TEXT NOT NULL,
            company TEXT,
            phone TEXT NOT NULL,
            phone10 TEXT NOT NULL,
            rera_agent_no TEXT,
            code TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_broker_firm_phone UNIQUE (firm_id, phone10),
            CONSTRAINT uq_broker_firm_code UNIQUE (firm_id, code)
        )""",
        f'CREATE INDEX IF NOT EXISTS ix_brokers_firm ON "{SCHEMA}".brokers(firm_id)',
        f'CREATE INDEX IF NOT EXISTS ix_brokers_phone10 ON "{SCHEMA}".brokers(phone10)',
        f'ALTER TABLE "{SCHEMA}".leads ADD COLUMN IF NOT EXISTS broker_id UUID REFERENCES "{SCHEMA}".brokers(id) ON DELETE SET NULL',
        f'ALTER TABLE "{SCHEMA}".leads ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES "{SCHEMA}".projects(id) ON DELETE SET NULL',
        f'CREATE INDEX IF NOT EXISTS ix_leads_broker ON "{SCHEMA}".leads(broker_id)',
        f'CREATE INDEX IF NOT EXISTS ix_leads_project ON "{SCHEMA}".leads(project_id)',
        f"""CREATE TABLE IF NOT EXISTS "{SCHEMA}".lead_registrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES "{SCHEMA}".firms(id),
            project_id UUID REFERENCES "{SCHEMA}".projects(id) ON DELETE SET NULL,
            broker_id UUID REFERENCES "{SCHEMA}".brokers(id) ON DELETE SET NULL,
            lead_id UUID REFERENCES "{SCHEMA}".leads(id) ON DELETE SET NULL,
            reference_id TEXT NOT NULL UNIQUE,
            client_name TEXT,
            client_phone10 TEXT NOT NULL,
            method TEXT DEFAULT 'broker_whatsapp',
            status TEXT DEFAULT 'registered',
            conflict_with UUID REFERENCES "{SCHEMA}".lead_registrations(id) ON DELETE SET NULL,
            conflict_kind TEXT,
            conflict_state TEXT,
            resolution_note TEXT,
            resolved_by TEXT,
            resolved_at TIMESTAMPTZ,
            submitted_by_phone TEXT,
            source_wamid TEXT,
            registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until TIMESTAMPTZ
        )""",
        f'CREATE INDEX IF NOT EXISTS ix_reg_firm ON "{SCHEMA}".lead_registrations(firm_id)',
        f'CREATE INDEX IF NOT EXISTS ix_reg_phone ON "{SCHEMA}".lead_registrations(client_phone10)',
        f'CREATE INDEX IF NOT EXISTS ix_reg_broker ON "{SCHEMA}".lead_registrations(broker_id)',
        f'CREATE INDEX IF NOT EXISTS ix_reg_wamid ON "{SCHEMA}".lead_registrations(source_wamid)',
    ]
    for sql in stmts:
        conn.execute(sa.text(sql))


def downgrade() -> None:
    conn = op.get_bind()
    for sql in [
        f'DROP TABLE IF EXISTS "{SCHEMA}".lead_registrations',
        f'ALTER TABLE "{SCHEMA}".leads DROP COLUMN IF EXISTS broker_id',
        f'ALTER TABLE "{SCHEMA}".leads DROP COLUMN IF EXISTS project_id',
        f'DROP TABLE IF EXISTS "{SCHEMA}".brokers',
        f'DROP TABLE IF EXISTS "{SCHEMA}".projects',
    ]:
        conn.execute(sa.text(sql))
