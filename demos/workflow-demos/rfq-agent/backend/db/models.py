from sqlalchemy import Column, String, Text, Float, Integer, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from db.database import Base


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String, unique=True, index=True, nullable=False)
    token_json = Column(Text, nullable=False)
    watch_expiry = Column(DateTime(timezone=True), nullable=True)
    history_id = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class RFQSubmission(Base):
    __tablename__ = "rfq_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    rfq_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))

    # Intake
    source = Column(String, nullable=False)          # "email" | "whatsapp" | "upload"
    sender = Column(String, nullable=False)
    subject = Column(Text, nullable=True)
    email_id = Column(String, nullable=True)
    thread_id = Column(String, nullable=True, index=True)

    # Buyer info
    buyer_name = Column(Text, nullable=True)
    buyer_contact = Column(Text, nullable=True)
    delivery_location = Column(Text, nullable=True)
    rfq_deadline = Column(Text, nullable=True)
    special_instructions = Column(JSONB, nullable=True)

    # Classification
    urgency = Column(String, nullable=True)
    complexity = Column(String, nullable=True)
    category = Column(String, nullable=True)

    # Parsed data
    line_items = Column(JSONB, nullable=True)
    catalog_matches = Column(JSONB, nullable=True)
    feasibility = Column(JSONB, nullable=True)
    unfulfillable_items = Column(JSONB, nullable=True)

    # Pricing
    line_pricing = Column(JSONB, nullable=True)
    subtotal = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    pricing_confidence = Column(Float, nullable=True)

    # Output & Dispatch
    draft_quote = Column(Text, nullable=True)
    pdf_path = Column(Text, nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)

    # Follow-up sequence flags
    day3_followup_sent = Column(Boolean, default=False, nullable=False)
    day7_followup_sent = Column(Boolean, default=False, nullable=False)
    day14_followup_sent = Column(Boolean, default=False, nullable=False)

    # Status
    status = Column(String, nullable=False, default="processing")
    review_notes = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # Document + RFQ type + freight fields
    document_type = Column(String, nullable=True, default="RFQ")
    rfq_type = Column(String, nullable=True, default="product")
    freight_origin = Column(Text, nullable=True)
    freight_destination = Column(Text, nullable=True)
    freight_cargo_desc = Column(Text, nullable=True)
    freight_weight_kg = Column(Float, nullable=True)
    freight_volume_cbm = Column(Float, nullable=True)
    freight_truck_type = Column(String, nullable=True)
    freight_distance_km = Column(Float, nullable=True)
    freight_quote_amount = Column(Float, nullable=True)
