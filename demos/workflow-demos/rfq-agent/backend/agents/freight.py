import logging
from langchain_core.messages import SystemMessage, HumanMessage

from workflow.state import RFQState
from models.gemini_models import get_gemini
from models.structured_output import FreightRFQ
from prompts.rfq_prompts import FREIGHT_PROMPT

logger = logging.getLogger(__name__)

_llm = get_gemini()
_structured_llm = _llm.with_structured_output(FreightRFQ)

TRUCK_RATES = {
    "mini":    {"base": 1500,  "per_km": 12,  "label": "Mini Truck / Tempo (< 1 ton)"},
    "medium":  {"base": 2500,  "per_km": 18,  "label": "Medium Truck / Canter (1–5 ton)"},
    "large":   {"base": 4000,  "per_km": 25,  "label": "Large Truck (5–15 ton)"},
    "trailer": {"base": 6000,  "per_km": 35,  "label": "Trailer / Multi-axle (15+ ton)"},
}

RUSH_PREMIUMS = {"critical": 0.25, "rush": 0.15, "standard": 0.00}


def freight_node(state: RFQState) -> dict:
    logger.info(f"[FREIGHT] RFQ {state['rfq_id']} — extracting freight details")

    try:
        result: FreightRFQ = _structured_llm.invoke([
            SystemMessage(content=FREIGHT_PROMPT),
            HumanMessage(content=f"Parse this freight RFQ:\n\n{state['raw_content']}"),
        ])
    except Exception as e:
        logger.error(f"[FREIGHT] Parse failed for RFQ {state['rfq_id']}: {e}")
        return {
            "error": f"Freight parser failed: {e}",
            "complexity": "review",
            "urgency": "standard",
        }

    truck_type = (result.truck_type or "large").lower()
    if truck_type not in TRUCK_RATES:
        truck_type = "large"

    distance_km = result.distance_km or 500.0
    urgency = result.urgency or "standard"
    rush_premium = RUSH_PREMIUMS.get(urgency, 0.0)

    rates = TRUCK_RATES[truck_type]
    base_amount = rates["base"] + rates["per_km"] * distance_km
    freight_amount = round(base_amount * (1 + rush_premium), 2)

    # Flag for human review if heavy customisation requested
    complexity = "review" if result.special_requirements else "auto"

    logger.info(
        f"[FREIGHT] {result.origin} → {result.destination} | "
        f"{truck_type} | ~{distance_km}km | ₹{freight_amount:,.2f} | urgency={urgency}"
    )

    return {
        "freight_origin": result.origin,
        "freight_destination": result.destination,
        "freight_cargo_desc": result.cargo_desc,
        "freight_weight_kg": result.weight_kg,
        "freight_volume_cbm": result.volume_cbm,
        "freight_truck_type": truck_type,
        "freight_distance_km": distance_km,
        "freight_quote_amount": freight_amount,
        "total": freight_amount,
        "subtotal": freight_amount,
        "pricing_confidence": 0.82,
        "urgency": urgency,
        "complexity": complexity,
        "category": "freight_logistics",
        "unfulfillable_items": [],
        "catalog_matches": [],
        "feasibility": [],
        "line_pricing": [],
    }
