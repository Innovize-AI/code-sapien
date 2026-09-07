from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class RFQUploadResponse(BaseModel):
    rfq_id: str
    status: str
    total: Optional[float] = None
    pricing_confidence: Optional[float] = None
    line_items_count: int
    draft_quote: Optional[str] = None
    review_notes: Optional[str] = None
    rfq_type: Optional[str] = None


class RFQListItem(BaseModel):
    rfq_id: str
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    source: str
    sender: str
    email_id: Optional[str] = None
    buyer_name: Optional[str] = None
    urgency: Optional[str] = None
    category: Optional[str] = None
    rfq_type: Optional[str] = "product"
    total: Optional[float] = None
    pricing_confidence: Optional[float] = None
    status: str

    class Config:
        from_attributes = True


class RFQListResponse(BaseModel):
    items: List[RFQListItem]
    total: int
    page: int
    limit: int


class RFQDetail(BaseModel):
    rfq_id: str
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    source: str
    sender: str
    subject: Optional[str] = None
    email_id: Optional[str] = None
    thread_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_contact: Optional[str] = None
    delivery_location: Optional[str] = None
    rfq_deadline: Optional[str] = None
    special_instructions: Optional[List[str]] = None
    urgency: Optional[str] = None
    complexity: Optional[str] = None
    category: Optional[str] = None
    rfq_type: Optional[str] = "product"
    line_items: Optional[Any] = None
    catalog_matches: Optional[Any] = None
    feasibility: Optional[Any] = None
    unfulfillable_items: Optional[Any] = None
    line_pricing: Optional[Any] = None
    subtotal: Optional[float] = None
    total: Optional[float] = None
    pricing_confidence: Optional[float] = None
    draft_quote: Optional[str] = None
    status: str
    review_notes: Optional[str] = None
    error: Optional[str] = None
    freight_origin: Optional[str] = None
    freight_destination: Optional[str] = None
    freight_cargo_desc: Optional[str] = None
    freight_weight_kg: Optional[float] = None
    freight_volume_cbm: Optional[float] = None
    freight_truck_type: Optional[str] = None
    freight_distance_km: Optional[float] = None
    freight_quote_amount: Optional[float] = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total: int
    dispatched: int
    pending_review: int
    processing: int
    failed: int
    total_value: float


class TextRFQRequest(BaseModel):
    raw_text: str
    sender: str
    subject: Optional[str] = None
