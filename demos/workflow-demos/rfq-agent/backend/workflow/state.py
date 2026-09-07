from typing import Annotated, TypedDict, Optional, List, Union
import operator


def reduce_last(left, right):
    """Always takes the latest value. Handles list of updates from parallel nodes."""
    if isinstance(right, list):
        if not right:
            return left
        if len(right) > 0 and isinstance(right[0], list):
            return right[-1]
    return right


def reduce_append(left: list, right: Union[list, dict]) -> list:
    """Appends items from parallel nodes into a single list."""
    if left is None:
        left = []
    if isinstance(right, list):
        return left + right
    if isinstance(right, dict):
        return left + [right]
    return left


class LineItem(TypedDict):
    description: str
    quantity: Optional[float]
    unit: Optional[str]
    specs: Optional[str]
    delivery_date: Optional[str]


class CatalogMatch(TypedDict):
    line_item_index: int
    product_id: str
    product_name: str
    unit_price: float
    available: bool
    lead_time_days: int
    confidence: float
    notes: Optional[str]


class FeasibilityResult(TypedDict):
    line_item_index: int
    feasible: bool
    reason: Optional[str]
    alternative: Optional[str]


class LinePrice(TypedDict):
    line_item_index: int
    unit_price: float
    quantity: float
    subtotal: float
    discount_pct: float
    rush_premium_pct: float
    notes: Optional[str]


class RFQState(TypedDict):
    # Intake
    rfq_id: str
    source: str                              # "email" | "whatsapp" | "upload"
    sender: str
    raw_content: str
    attachment_path: Optional[str]
    attachment_url: Optional[str]
    subject: Optional[str]
    email_id: Optional[str]
    thread_id: Optional[str]

    # Document + RFQ type — set by parser, drives graph branching
    document_type: Annotated[Optional[str], reduce_last]  # "RFQ" | "BOQ" | "Lane Bid" | "Stores Requisition" | "Purchase Order" | "Invoice" | "Unknown"
    rfq_type: Annotated[Optional[str], reduce_last]       # "product" | "freight"

    # Parsing
    line_items: Annotated[List[LineItem], reduce_last]
    missing_fields: Annotated[List[str], reduce_last]
    special_instructions: Annotated[List[str], reduce_last]
    buyer_name: Annotated[Optional[str], reduce_last]
    buyer_contact: Annotated[Optional[str], reduce_last]
    delivery_location: Annotated[Optional[str], reduce_last]
    rfq_deadline: Annotated[Optional[str], reduce_last]

    # Classification (parallel with parse)
    urgency: Annotated[str, reduce_last]     # "standard" | "rush" | "critical"
    complexity: Annotated[str, reduce_last]  # "auto" | "review"
    category: Annotated[Optional[str], reduce_last]

    # Freight-specific fields (only populated when rfq_type == "freight")
    freight_origin: Annotated[Optional[str], reduce_last]
    freight_destination: Annotated[Optional[str], reduce_last]
    freight_cargo_desc: Annotated[Optional[str], reduce_last]
    freight_weight_kg: Annotated[Optional[float], reduce_last]
    freight_volume_cbm: Annotated[Optional[float], reduce_last]
    freight_truck_type: Annotated[Optional[str], reduce_last]  # "mini" | "medium" | "large" | "trailer"
    freight_distance_km: Annotated[Optional[float], reduce_last]
    freight_quote_amount: Annotated[Optional[float], reduce_last]

    # Intelligence (parallel fan-out)
    catalog_matches: Annotated[List[CatalogMatch], reduce_append]
    feasibility: Annotated[List[FeasibilityResult], reduce_append]
    unfulfillable_items: Annotated[List[int], operator.add]

    # Pricing
    line_pricing: Annotated[List[LinePrice], reduce_last]
    subtotal: Annotated[float, reduce_last]
    total: Annotated[float, reduce_last]
    pricing_confidence: Annotated[float, reduce_last]

    # Output
    draft_quote: Annotated[Optional[str], reduce_last]
    pdf_path: Annotated[Optional[str], reduce_last]

    # Routing
    status: Annotated[str, reduce_last]      # "processing" | "auto_approved" | "pending_review" | "dispatched" | "failed"
    review_notes: Annotated[Optional[str], reduce_last]
    error: Annotated[Optional[str], reduce_last]
