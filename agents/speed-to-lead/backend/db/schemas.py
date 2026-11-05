from __future__ import annotations
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class FirmOut(BaseModel):
    id: UUID
    name: str
    vertical: str
    is_active: bool
    wa_phone_number_id: str | None
    firm_display_name: str | None
    visit_cta: str | None
    booking_link: str | None
    maps_link: str | None
    fallback_alert_email: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadOut(BaseModel):
    id: UUID
    firm_id: UUID | None
    phone: str
    wa_name: str | None
    lead_name: str | None
    lead_type: str | None
    is_qualified: bool
    lead_status: str
    ai_paused: bool
    ctwa_source_id: str | None
    created_at: datetime
    last_active: datetime

    class Config:
        from_attributes = True


class LeadWithStageOut(LeadOut):
    stage: str | None = None
    turn_count: int | None = None
    last_message_at: datetime | None = None


class InteriorProfileOut(BaseModel):
    lead_id: UUID
    config: str | None
    budget_bracket: str | None
    scope: str | None
    design_style: str | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class RealEstateProfileOut(BaseModel):
    lead_id: UUID
    config: str | None
    budget_bracket: str | None
    property_location: str | None
    cab_pickup_address: str | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class SolarProfileOut(BaseModel):
    lead_id: UUID
    property_type: str | None
    monthly_bill_bracket: str | None
    system_size_kw: str | None
    roof_ownership: str | None
    location_city: str | None
    subsidy_eligible: bool | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: UUID
    lead_id: UUID
    firm_id: UUID | None
    stage: str
    turn_count: int
    context: dict[str, Any]
    last_message_at: datetime

    class Config:
        from_attributes = True


class VisitOut(BaseModel):
    id: UUID
    firm_id: UUID | None
    lead_id: UUID
    visit_date: date
    visit_time_slot: str | None
    cab_pickup_address: str | None
    status: str | None
    hesitation_code: str | None
    attended: bool | None
    outcome: str | None
    cancellation_reason: str | None
    # joined from leads
    lead_name: str | None = None
    lead_type: str | None = None
    phone: str | None = None

    class Config:
        from_attributes = True


class ConversationLogOut(BaseModel):
    id: UUID
    firm_id: UUID | None
    session_id: UUID | None
    lead_id: UUID | None
    direction: str
    sender_type: str
    message_text: str | None
    path_taken: str | None
    pinecone_score: float | None
    turn_number: int | None
    created_at: datetime
    resource_sent: str | None = None        # id of the brochure or video attached to this reply
    resource: dict | None = None            # its title, type and link, so the page can show it

    class Config:
        from_attributes = True


class RetrievalLogOut(BaseModel):
    id: UUID
    turn_number: int | None
    query_original: str
    knowledge_top_score: float | None
    knowledge_chunks: list[dict] | None
    portfolio_matches: list[dict] | None
    confidence_gate_passed: bool | None
    resource_attached: bool | None
    tools_called: list[str] | None
    path_taken: str
    pinecone_latency_ms: int | None
    claude_latency_ms: int | None
    total_latency_ms: int | None
    created_at: datetime

    class Config:
        from_attributes = True
