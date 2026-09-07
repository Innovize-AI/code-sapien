from pydantic import BaseModel, Field
from typing import List, Optional


class LineItem(BaseModel):
    description: str = Field(description="Description of the requested item or service")
    quantity: Optional[float] = Field(None, description="Requested quantity")
    unit: Optional[str] = Field(None, description="Unit of measure (pcs, kg, meters, etc.)")
    specs: Optional[str] = Field(None, description="Technical specifications or requirements")
    delivery_date: Optional[str] = Field(None, description="Requested delivery date for this item")


class ParsedRFQ(BaseModel):
    document_type: str = Field(
        "RFQ",
        description=(
            "Type of document received. Choose the best match: "
            "'RFQ' (standard request for quotation, plain email or text), "
            "'BOQ' (Bill of Quantities — structured list with item refs, categories, project codes), "
            "'Lane Bid' (freight lane bid sheet — origin/destination/equipment columns), "
            "'Stores Requisition' (ship chandler list — IMPA/ISSA codes, vessel name, port), "
            "'Purchase Order' (buyer is placing an order, not requesting a quote), "
            "'Invoice' (billing document from supplier), "
            "'Unknown' (cannot determine)."
        ),
    )
    rfq_type: str = Field("product", description="Type of RFQ: 'freight' for transport/logistics/truck/shipping requests, 'product' for goods, materials, equipment")
    buyer_name: Optional[str] = Field(None, description="Name of the buyer or company sending the RFQ")
    buyer_contact: Optional[str] = Field(None, description="Email or phone of the buyer")
    delivery_location: Optional[str] = Field(None, description="Delivery address or location")
    rfq_deadline: Optional[str] = Field(None, description="Deadline to respond to this RFQ")
    missing_fields: List[str] = Field(default_factory=list, description="Important fields that are missing or unclear")
    line_items: List[LineItem] = Field(default_factory=list, description="List of items being requested. Leave empty for freight RFQs.")
    special_instructions: List[str] = Field(default_factory=list, description="Any special terms, constraints, warranties, SLAs, delivery conditions, or certifications requested by the buyer.")


class FreightRFQ(BaseModel):
    origin: str = Field(description="Pickup city or address")
    destination: str = Field(description="Delivery city or address")
    cargo_desc: Optional[str] = Field(None, description="Description of cargo or goods to be transported")
    weight_kg: Optional[float] = Field(None, description="Total cargo weight in kilograms")
    volume_cbm: Optional[float] = Field(None, description="Cargo volume in cubic metres")
    truck_type: str = Field("large", description="Truck size: 'mini' (< 1 ton), 'medium' (1-5 ton), 'large' (5-15 ton), 'trailer' (15+ ton)")
    distance_km: Optional[float] = Field(None, description="Estimated road distance in km. Estimate from common Indian city pairs if not stated.")
    urgency: str = Field("standard", description="critical (< 24 hrs), rush (1-3 days), standard (> 3 days or not specified)")
    special_requirements: Optional[str] = Field(None, description="Any special transport requirements like refrigeration, hazmat, insurance, etc.")


class RFQClassification(BaseModel):
    urgency: str = Field(description="critical (< 3 days), rush (3-7 days), or standard (> 7 days / no deadline)")
    complexity: str = Field(description="auto (standard items, clear specs, < 20 items) or review (custom specs, unclear requirements, > 20 items)")
    category: str = Field(description="Product category: industrial_components, raw_materials, services, it_hardware, packaging, or other")


class FeasibilityItem(BaseModel):
    line_item_index: int = Field(description="Index of the line item (0-based)")
    feasible: bool = Field(description="Whether this item can be fulfilled")
    reason: Optional[str] = Field(None, description="Reason if not feasible")
    alternative: Optional[str] = Field(None, description="Alternative product or suggestion if not feasible")


class FeasibilityReport(BaseModel):
    items: List[FeasibilityItem] = Field(description="Feasibility result for each line item")
