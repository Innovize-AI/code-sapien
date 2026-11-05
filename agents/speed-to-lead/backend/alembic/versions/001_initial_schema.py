"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "stl"


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), server_default=sa.text("'pdf'"), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("vertical", sa.Text(), server_default=sa.text("'both'"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("wa_name", sa.Text(), nullable=True),
        sa.Column("lead_name", sa.Text(), nullable=True),
        sa.Column("lead_type", sa.Text(), nullable=True),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("budget_bracket", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("design_style", sa.Text(), nullable=True),
        sa.Column("is_qualified", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("disqualified_reason", sa.Text(), nullable=True),
        sa.Column("ctwa_source_id", sa.Text(), nullable=True),
        sa.Column("ctwa_config", sa.Text(), nullable=True),
        sa.Column("ctwa_location", sa.Text(), nullable=True),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("visit_time_slot", sa.Text(), nullable=True),
        sa.Column("cab_pickup_address", sa.Text(), nullable=True),
        sa.Column("lead_status", sa.Text(), server_default=sa.text("'new'"), nullable=True),
        sa.Column("ai_paused", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("fallback_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("source", sa.Text(), server_default=sa.text("'organic'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_active", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("lead_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_leads_phone", "leads", ["phone"], unique=True, schema=SCHEMA)
    op.create_index("ix_stl_leads_lead_status", "leads", ["lead_status"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_leads_last_active", "leads", ["last_active"], unique=False, schema=SCHEMA)
    op.create_index(
        "idx_leads_ai_paused", "leads", ["ai_paused"], unique=False,
        schema=SCHEMA, postgresql_where=sa.text("ai_paused = true"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("context", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column("turn_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("stage", sa.Text(), server_default=sa.text("'discovery'"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_sessions_lead_id", "sessions", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_sessions_last_message_at", "sessions", ["last_message_at"], unique=False, schema=SCHEMA)
    op.create_index(
        "idx_sessions_active", "sessions", ["ended_at"], unique=False,
        schema=SCHEMA, postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("visit_time_slot", sa.Text(), nullable=True),
        sa.Column("cab_pickup_address", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'scheduled'"), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("hesitation_code", sa.Text(), nullable=True),
        sa.Column("confirmed_by_agent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attended", sa.Boolean(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("team_notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_visits_lead_id", "visits", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_visits_visit_date", "visits", ["visit_date"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_visits_status", "visits", ["status"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_visits_attended", "visits", ["attended"], unique=False, schema=SCHEMA)

    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("sender_type", sa.Text(), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("path_taken", sa.Text(), nullable=True),
        sa.Column("pinecone_score", sa.Float(), nullable=True),
        sa.Column("resource_sent", sa.Text(), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("wa_message_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_logs_session_id", "conversation_logs", ["session_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_logs_lead_id", "conversation_logs", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_logs_created_at", "conversation_logs", ["created_at"], unique=False, schema=SCHEMA)
    op.create_index(
        "idx_logs_wa_msg_id", "conversation_logs", ["wa_message_id"], unique=False,
        schema=SCHEMA, postgresql_where=sa.text("wa_message_id IS NOT NULL"),
    )

    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("query_original", sa.Text(), nullable=False),
        sa.Column("knowledge_top_score", sa.Float(), nullable=True),
        sa.Column("knowledge_chunks", postgresql.JSONB(), nullable=True),
        sa.Column("portfolio_matches", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_gate_passed", sa.Boolean(), nullable=True),
        sa.Column("resource_attached", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("tools_called", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("pinecone_latency_ms", sa.Integer(), nullable=True),
        sa.Column("claude_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("path_taken", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_rlogs_session_id", "retrieval_logs", ["session_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_rlogs_lead_id", "retrieval_logs", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_rlogs_knowledge_top_score", "retrieval_logs", ["knowledge_top_score"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_rlogs_path_taken", "retrieval_logs", ["path_taken"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_rlogs_created_at", "retrieval_logs", ["created_at"], unique=False, schema=SCHEMA)
    op.create_index(
        "idx_rlogs_fallback", "retrieval_logs", ["created_at"], unique=False,
        schema=SCHEMA, postgresql_where=sa.text("path_taken = 'fallback'"),
    )

    op.create_table(
        "followup_schedules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("sequence", sa.Text(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_followup_lead_id", "followup_schedules", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_followup_status", "followup_schedules", ["status"], unique=False, schema=SCHEMA)

    op.create_table(
        "broadcast_campaigns",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("template_language", sa.Text(), server_default=sa.text("'en'"), nullable=True),
        sa.Column("target_statuses", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("message_preview", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_sent", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_delivered", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_replied", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_table(
        "broadcast_sends",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("wa_message_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], [f"{SCHEMA}.broadcast_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], [f"{SCHEMA}.leads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "lead_id", name="uq_bc_send"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_stl_bc_sends_campaign_id", "broadcast_sends", ["campaign_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_bc_sends_lead_id", "broadcast_sends", ["lead_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_stl_bc_sends_status", "broadcast_sends", ["status"], unique=False, schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("broadcast_sends", schema=SCHEMA)
    op.drop_table("broadcast_campaigns", schema=SCHEMA)
    op.drop_table("followup_schedules", schema=SCHEMA)
    op.drop_table("retrieval_logs", schema=SCHEMA)
    op.drop_table("conversation_logs", schema=SCHEMA)
    op.drop_table("visits", schema=SCHEMA)
    op.drop_table("sessions", schema=SCHEMA)
    op.drop_table("leads", schema=SCHEMA)
    op.drop_table("resources", schema=SCHEMA)
