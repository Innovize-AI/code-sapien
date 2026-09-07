import os
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from workflow.state import RFQState
from models.gemini_models import get_gemini
from prompts.rfq_prompts import DRAFTER_PROMPT, FREIGHT_DRAFTER_PROMPT

logger = logging.getLogger(__name__)

_llm = get_gemini()

TRUCK_LABELS = {
    "mini":    "Mini Truck / Tempo (< 1 ton)",
    "medium":  "Medium Truck / Canter (1–5 ton)",
    "large":   "Large Truck (5–15 ton)",
    "trailer": "Trailer / Multi-axle (15+ ton)",
}


def _build_freight_context(state: RFQState) -> tuple[str, str]:
    company_name = os.getenv("COMPANY_NAME", "Our Company")
    system_prompt = FREIGHT_DRAFTER_PROMPT.format(company_name=company_name)
    truck_type = state.get("freight_truck_type", "large")
    rush_premium = state.get("freight_quote_amount", 0) - (
        state.get("freight_distance_km", 0) * {"mini": 12, "medium": 18, "large": 25, "trailer": 35}.get(truck_type, 25)
        + {"mini": 1500, "medium": 2500, "large": 4000, "trailer": 6000}.get(truck_type, 4000)
    )
    special_inst = state.get("special_instructions") or []
    special_inst_text = "\n".join(f"- {inst}" for inst in special_inst) if special_inst else "None"

    context = f"""
Buyer: {state.get('buyer_name', 'Valued Customer')}
Urgency: {state.get('urgency', 'standard')}
RFQ deadline: {state.get('rfq_deadline', 'Not specified')}

Route: {state.get('freight_origin', '—')} → {state.get('freight_destination', '—')}
Cargo: {state.get('freight_cargo_desc', 'Not specified')}
Weight: {state.get('freight_weight_kg', 'Not specified')} kg
Volume: {state.get('freight_volume_cbm', 'Not specified')} CBM
Truck type: {TRUCK_LABELS.get(truck_type, truck_type)}
Estimated distance: {state.get('freight_distance_km', '—')} km
Total freight charge: ₹{state.get('freight_quote_amount', 0):,.2f}
Rush surcharge applied: ₹{max(0, rush_premium):,.2f}
Special requirements: {state.get('freight_cargo_desc', 'None')}

Special Instructions / Terms Requested by Buyer (Ensure these are addressed in your quote):
{special_inst_text}
"""
    return system_prompt, context


def _build_product_context(state: RFQState) -> tuple[str, str]:
    company_name = os.getenv("COMPANY_NAME", "Our Company")
    system_prompt = DRAFTER_PROMPT.format(company_name=company_name)

    matches_by_index = {m["line_item_index"]: m for m in state.get("catalog_matches", [])}
    pricing_by_index = {p["line_item_index"]: p for p in state.get("line_pricing", [])}
    unfulfillable_indices = state.get("unfulfillable_items") or []
    feasibility_by_index = {f["line_item_index"]: f for f in state.get("feasibility", [])}

    items_summary = []
    unfulfillable_summary = []
    for i, item in enumerate(state.get("line_items", [])):
        match = matches_by_index.get(i, {})
        pricing = pricing_by_index.get(i, {})
        
        if i in unfulfillable_indices:
            feas = feasibility_by_index.get(i, {})
            alt_text = f" (Suggested alternative: {feas['alternative']})" if feas.get("alternative") else ""
            unfulfillable_summary.append(f"- {item['description']}{alt_text}")
        else:
            items_summary.append(
                f"- {item['description']} | Qty: {item.get('quantity', 'TBD')} {item.get('unit', '')} | "
                f"Unit Price: ₹{pricing.get('unit_price', 'TBD')} | "
                f"Subtotal: ₹{pricing.get('subtotal', 'TBD')} | "
                f"Lead time: {match.get('lead_time_days', 'TBD')} days"
            )

    special_inst = state.get("special_instructions") or []
    special_inst_text = "\n".join(f"- {inst}" for inst in special_inst) if special_inst else "None"

    context = f"""
Buyer: {state.get('buyer_name', 'Valued Customer')}
Urgency: {state.get('urgency', 'standard')}
Delivery location: {state.get('delivery_location', 'Not specified')}
RFQ deadline: {state.get('rfq_deadline', 'Not specified')}

Fulfillable Line Items (Include only these in the quotation table):
{chr(10).join(items_summary)}

Total: ₹{state.get('total', 0):,.2f}

Unfulfillable / Out-of-Stock Items (Do NOT include these in the quotation table, list them separately in the response email body with apologies and suggested alternatives):
{chr(10).join(unfulfillable_summary) if unfulfillable_summary else "None"}

Special Instructions / Terms Requested by Buyer (Ensure these are addressed in your quote):
{special_inst_text}
"""
    return system_prompt, context


def draft_node(state: RFQState) -> dict:
    logger.info(f"[DRAFTER] RFQ {state['rfq_id']} — generating quotation draft (type={state.get('rfq_type', 'product')})")

    if state.get("rfq_type") == "freight":
        system_prompt, context = _build_freight_context(state)
    else:
        system_prompt, context = _build_product_context(state)

    try:
        response = _llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Write the quotation:\n{context}"),
        ])
        content = response.content
        if isinstance(content, list):
            draft = " ".join(
                block["text"] for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            draft = content
    except Exception as e:
        logger.error(f"[DRAFTER] Failed for RFQ {state['rfq_id']}: {e}")
        draft = None

    return {"draft_quote": draft}
