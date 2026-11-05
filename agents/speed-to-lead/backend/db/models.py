from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, Date,
    DateTime, ForeignKey, text, ARRAY, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB  # JSONB kept for Session.context, etc.

from db.database import Base
from db.config import SCHEMA


def _fk(table: str, col: str = "id", **kw) -> ForeignKey:
    return ForeignKey(f"{SCHEMA}.{table}.{col}", **kw)


class Plan(Base):
    """Subscription plan tiers — one row per tier, referenced by firms."""
    __tablename__ = "plans"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name             = Column(Text, nullable=False, unique=True)    # organic_starter | growth | pro | scale
    label            = Column(Text, nullable=False)                 # display label
    monthly_chat_cap = Column(Integer, nullable=False)
    price_monthly    = Column(Integer, nullable=False)              # INR ex-GST
    overage_per_chat = Column(Integer, server_default=text("15"))   # INR per chat above cap
    created_at       = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class Firm(Base):
    """One record per client/firm. Drives vertical, WA credentials, and prompt config."""
    __tablename__ = "firms"

    id                      = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name                    = Column(Text, nullable=False)          # display name e.g. "Greenfield Solar"
    vertical                = Column(Text, nullable=False)          # interior | real_estate | solar
    is_active               = Column(Boolean, server_default=text("true"))
    plan_id                 = Column(UUID(as_uuid=True), _fk("plans"), nullable=True)
    monthly_chats_used      = Column(Integer, server_default=text("0"))
    usage_reset_at          = Column(DateTime(timezone=True), server_default=text("now()"))

    # WhatsApp Cloud API credentials (per firm)
    wa_phone_number_id      = Column(Text, unique=True)             # used to route webhook messages
    meta_access_token       = Column(Text)
    meta_app_secret         = Column(Text)
    meta_webhook_verify_token = Column(Text)

    # Prompt customization
    firm_display_name       = Column(Text)                          # shown in prompts as "[Firm Name]"
    visit_cta               = Column(Text)                          # e.g. "Experience Center visit"
    booking_link            = Column(Text)
    maps_link               = Column(Text)
    fallback_alert_email    = Column(Text)

    # Contact details injected into prompts; everything else lives in the knowledge base
    contact_phone           = Column(Text)
    contact_email           = Column(Text)

    created_at              = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at              = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class Resource(Base):
    __tablename__ = "resources"

    id            = Column(Text, primary_key=True)
    firm_id       = Column(UUID(as_uuid=True), _fk("firms"), index=True)
    title         = Column(Text, nullable=False)
    description   = Column(Text)
    resource_type = Column(Text, nullable=False, server_default=text("'pdf'"))
    url           = Column(Text)
    updated_at    = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class Lead(Base):
    """Common lead fields only. Vertical-specific qualification is in profile tables."""
    __tablename__ = "leads"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id             = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    phone               = Column(Text, nullable=False, index=True)
    wa_name             = Column(Text)
    lead_name           = Column(Text)
    lead_type           = Column(Text, index=True)               # denorm from firm.vertical: interior | real_estate | solar

    # CTWA attribution
    ctwa_source_id      = Column(Text)
    ctwa_config         = Column(Text)
    ctwa_location       = Column(Text)

    # Booking (kept here for pipeline state tracking)
    visit_date          = Column(Date)
    visit_time_slot     = Column(Text)

    # Qualification gate
    is_qualified        = Column(Boolean, server_default=text("false"))
    disqualified_reason = Column(Text)

    # Lifecycle
    lead_status         = Column(Text, server_default=text("'new'"), index=True)
    ai_paused           = Column(Boolean, server_default=text("false"))
    fallback_count      = Column(Integer, server_default=text("0"))
    source              = Column(Text, server_default=text("'organic'"))
    broker_id           = Column(UUID(as_uuid=True), _fk("brokers", ondelete="SET NULL"), index=True)
    project_id          = Column(UUID(as_uuid=True), _fk("projects", ondelete="SET NULL"), index=True)
    number_id           = Column(UUID(as_uuid=True), _fk("firm_numbers", ondelete="SET NULL"), index=True)
    owner_id            = Column(UUID(as_uuid=True), _fk("brokers", ondelete="SET NULL"), index=True)

    created_at          = Column(DateTime(timezone=True), server_default=text("now()"))
    last_active         = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
    lead_captured_at    = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("firm_id", "phone", name="uq_lead_firm_phone"),
        Index("idx_leads_ai_paused", "ai_paused", postgresql_where=text("ai_paused = true")),
        {"schema": SCHEMA},
    )


class Project(Base):
    """A developer's live project. Facts here are quoted by the agent (RERA, possession, price)."""
    __tablename__ = "projects"

    id                 = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id            = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    name               = Column(Text, nullable=False)
    location           = Column(Text)
    rera_number        = Column(Text)
    possession_date    = Column(Date)
    starting_price     = Column(Text)           # free text, e.g. "Rs. 1.45 Cr onwards (all-in)"
    payment_plan       = Column(Text)
    bank_tieups        = Column(Text)
    validity_days      = Column(Integer, server_default=text("60"))   # broker registration validity
    is_active          = Column(Boolean, server_default=text("true"))
    created_at         = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class Broker(Base):
    """A channel partner enrolled by a developer. Identity = their personal WhatsApp number."""
    __tablename__ = "brokers"

    id                 = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id            = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    name               = Column(Text, nullable=False)
    company            = Column(Text)
    phone              = Column(Text, nullable=False)       # as entered
    phone10            = Column(Text, nullable=False, index=True)  # last 10 digits, matching key
    rera_agent_no      = Column(Text)
    code               = Column(Text, nullable=False)       # coded link, e.g. BRK-RAV7
    kind               = Column(Text, server_default=text("'partner'"))  # partner | team
    email              = Column(Text)                       # login email once an account is created
    status             = Column(Text, server_default=text("'active'"))   # active | suspended
    created_at         = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("firm_id", "phone10", name="uq_broker_firm_phone"),
        UniqueConstraint("firm_id", "code", name="uq_broker_firm_code"),
        {"schema": SCHEMA},
    )


class FirmNumber(Base):
    """A WhatsApp number registered for a firm. A number may be attached to one person (a partner
    or a team member). Conversations that arrive on it belong to that person. A firm's own main
    number stays on firms.wa_phone_number_id and has no row here."""
    __tablename__ = "firm_numbers"

    id                = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id           = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    person_id         = Column(UUID(as_uuid=True), _fk("brokers", ondelete="SET NULL"), index=True)
    label             = Column(Text, nullable=False)
    display_phone     = Column(Text)                         # the number people dial, shown in the UI
    wa_phone_number_id = Column(Text, nullable=False, unique=True)   # Meta's ID for this number
    meta_access_token = Column(Text)                         # optional, falls back to the firm's token
    is_active         = Column(Boolean, server_default=text("true"))
    created_at        = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class LeadRegistration(Base):
    """Timestamped ownership record. The first valid registration for a client and project wins."""
    __tablename__ = "lead_registrations"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id          = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    project_id       = Column(UUID(as_uuid=True), _fk("projects", ondelete="SET NULL"), index=True)
    broker_id        = Column(UUID(as_uuid=True), _fk("brokers", ondelete="SET NULL"), index=True)
    lead_id          = Column(UUID(as_uuid=True), _fk("leads", ondelete="SET NULL"), index=True)
    reference_id     = Column(Text, nullable=False, unique=True)
    client_name      = Column(Text)
    client_phone10   = Column(Text, nullable=False, index=True)
    method           = Column(Text, server_default=text("'broker_whatsapp'"))  # broker_whatsapp | coded_link | form
    status           = Column(Text, server_default=text("'registered'"))
    # registered | duplicate | superseded | expired | rejected
    conflict_with    = Column(UUID(as_uuid=True), _fk("lead_registrations", ondelete="SET NULL"))
    conflict_kind    = Column(Text)             # broker_vs_broker | broker_vs_existing_lead
    conflict_state   = Column(Text)             # open | resolved
    resolution_note  = Column(Text)
    resolved_by      = Column(Text)
    resolved_at      = Column(DateTime(timezone=True))
    submitted_by_phone = Column(Text)           # raw sender, kept for rejected attempts
    source_wamid     = Column(Text, index=True)
    registered_at    = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    valid_until      = Column(DateTime(timezone=True))

    __table_args__ = {"schema": SCHEMA}


class LeadSummary(Base):
    """Cached AI summary of one lead's conversation. Regenerated when new messages arrive."""
    __tablename__ = "lead_summaries"

    lead_id        = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), primary_key=True)
    summary        = Column(JSONB, nullable=False)
    message_count  = Column(Integer, nullable=False, server_default=text("0"))
    model          = Column(Text)
    updated_at     = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class InteriorProfile(Base):
    """Qualification fields for interior design leads."""
    __tablename__ = "interior_profiles"

    lead_id         = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), primary_key=True)
    config          = Column(Text)          # 2BHK | 3BHK | 4BHK | Villa
    budget_bracket  = Column(Text)          # under_5L | 5-10L | 10-20L | 20L+
    scope           = Column(Text)          # full_home | specific_room
    design_style    = Column(Text)          # inferred from portfolio reaction
    updated_at      = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class RealEstateProfile(Base):
    """Qualification fields for real estate leads."""
    __tablename__ = "real_estate_profiles"

    lead_id             = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), primary_key=True)
    config              = Column(Text)      # 2BHK | 3BHK | 4BHK | Villa
    budget_bracket      = Column(Text)      # under_50L | 50L-1Cr | 1Cr-2Cr | 2Cr+
    property_location   = Column(Text)      # preferred area/project
    cab_pickup_address  = Column(Text)
    updated_at          = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class SolarProfile(Base):
    """Qualification fields for solar leads."""
    __tablename__ = "solar_profiles"

    lead_id               = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), primary_key=True)
    property_type         = Column(Text)    # residential | commercial | industrial
    monthly_bill_bracket  = Column(Text)    # under_2k | 2k-5k | 5k-10k | 10k+
    system_size_kw        = Column(Text)    # 1kW | 3kW | 5kW | 10kW | 10kW+
    roof_ownership        = Column(Text)    # owned | rented
    location_city         = Column(Text)
    subsidy_eligible      = Column(Boolean)
    updated_at            = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class Session(Base):
    __tablename__ = "sessions"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id         = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    lead_id         = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    context         = Column(JSONB, server_default=text("'{}'"))
    turn_count      = Column(Integer, server_default=text("0"))
    stage           = Column(Text, server_default=text("'discovery'"))
    started_at      = Column(DateTime(timezone=True), server_default=text("now()"))
    last_message_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
    ended_at        = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_sessions_active", "ended_at", postgresql_where=text("ended_at IS NULL")),
        {"schema": SCHEMA},
    )


class Visit(Base):
    __tablename__ = "visits"

    id                    = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id               = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    lead_id               = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    visit_date            = Column(Date, nullable=False, index=True)
    visit_time_slot       = Column(Text)
    cab_pickup_address    = Column(Text)
    status                = Column(Text, server_default=text("'scheduled'"), index=True)
    cancellation_reason   = Column(Text)
    hesitation_code       = Column(Text)
    confirmed_by_agent_at = Column(DateTime(timezone=True), server_default=text("now()"))
    reminder_sent_at      = Column(DateTime(timezone=True))
    attended              = Column(Boolean, index=True)
    outcome               = Column(Text)
    team_notes            = Column(Text)
    updated_at            = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id       = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    session_id    = Column(UUID(as_uuid=True), _fk("sessions", ondelete="CASCADE"), index=True)
    lead_id       = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    direction     = Column(Text, nullable=False)
    sender_type   = Column(Text, nullable=False)
    message_text  = Column(Text)
    media_type    = Column(Text)
    path_taken    = Column(Text)
    pinecone_score= Column(Float)
    resource_sent = Column(Text)
    turn_number   = Column(Integer)
    wa_message_id = Column(Text)
    number_id     = Column(UUID(as_uuid=True), _fk("firm_numbers", ondelete="SET NULL"), index=True)
    created_at    = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    __table_args__ = (
        Index("idx_logs_wa_msg_id", "wa_message_id", postgresql_where=text("wa_message_id IS NOT NULL")),
        {"schema": SCHEMA},
    )


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id                     = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id                = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    session_id             = Column(UUID(as_uuid=True), _fk("sessions", ondelete="CASCADE"), index=True)
    lead_id                = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    turn_number            = Column(Integer)
    query_original         = Column(Text, nullable=False)
    knowledge_top_score    = Column(Float, index=True)
    knowledge_chunks       = Column(JSONB)
    portfolio_matches      = Column(JSONB)
    confidence_gate_passed = Column(Boolean)
    resource_attached      = Column(Boolean, server_default=text("false"))
    tools_called           = Column(ARRAY(Text))
    pinecone_latency_ms    = Column(Integer)
    claude_latency_ms      = Column(Integer)
    total_latency_ms       = Column(Integer)
    path_taken             = Column(Text, nullable=False, index=True)
    created_at             = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    __table_args__ = (
        Index("idx_rlogs_fallback", "created_at", postgresql_where=text("path_taken = 'fallback'")),
        {"schema": SCHEMA},
    )


class FollowupSchedule(Base):
    __tablename__ = "followup_schedules"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id       = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    lead_id       = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    sequence      = Column(Text, nullable=False)
    day           = Column(Integer, nullable=False)
    template_name = Column(Text, nullable=False)
    variables     = Column(JSONB, server_default=text("'{}'"))
    scheduled_at  = Column(DateTime(timezone=True), nullable=False)
    sent_at       = Column(DateTime(timezone=True))
    status        = Column(Text, server_default=text("'pending'"), index=True)
    created_at    = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"

    id                = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    firm_id           = Column(UUID(as_uuid=True), _fk("firms"), nullable=False, index=True)
    name              = Column(Text, nullable=False)
    template_name     = Column(Text, nullable=False)
    template_language = Column(Text, server_default=text("'en'"))
    target_statuses   = Column(ARRAY(Text))
    message_preview   = Column(Text)
    scheduled_at      = Column(DateTime(timezone=True))
    sent_at           = Column(DateTime(timezone=True))
    total_sent        = Column(Integer, server_default=text("0"))
    total_delivered   = Column(Integer, server_default=text("0"))
    total_replied     = Column(Integer, server_default=text("0"))
    created_by        = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = {"schema": SCHEMA}


class BroadcastSend(Base):
    __tablename__ = "broadcast_sends"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    campaign_id   = Column(UUID(as_uuid=True), _fk("broadcast_campaigns", ondelete="CASCADE"), index=True)
    lead_id       = Column(UUID(as_uuid=True), _fk("leads", ondelete="CASCADE"), index=True)
    wa_message_id = Column(Text)
    status        = Column(Text, server_default=text("'pending'"), index=True)
    error_message = Column(Text)
    sent_at       = Column(DateTime(timezone=True))
    delivered_at  = Column(DateTime(timezone=True))
    read_at       = Column(DateTime(timezone=True))
    replied_at    = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_bc_send"),
        {"schema": SCHEMA},
    )
