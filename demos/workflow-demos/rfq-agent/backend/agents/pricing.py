import logging
from workflow.state import RFQState, LinePrice

logger = logging.getLogger(__name__)

VOLUME_DISCOUNT_TIERS = [
    (100, 0.10),
    (50,  0.07),
    (20,  0.05),
    (10,  0.02),
]

RUSH_PREMIUMS = {
    "critical": 0.20,
    "rush":     0.10,
    "standard": 0.00,
}


def _volume_discount(qty: float) -> float:
    for threshold, discount in VOLUME_DISCOUNT_TIERS:
        if qty >= threshold:
            return discount
    return 0.0


def pricing_node(state: RFQState) -> dict:
    logger.info(f"[PRICING] RFQ {state['rfq_id']} — pricing {len(state.get('line_items', []))} items")
    matches_by_index = {m["line_item_index"]: m for m in state.get("catalog_matches", [])}
    urgency = state.get("urgency", "standard")
    rush_premium = RUSH_PREMIUMS.get(urgency, 0.0)

    line_pricing: list[LinePrice] = []
    total_confidence = 0.0

    unfulfillable_indices = state.get("unfulfillable_items") or []

    for i, item in enumerate(state.get("line_items", [])):
        match = matches_by_index.get(i)
        qty = item.get("quantity") or 1.0
        is_unfulfillable = i in unfulfillable_indices

        if not match or match["product_id"] == "NOT_FOUND" or is_unfulfillable:
            line_pricing.append(LinePrice(
                line_item_index=i,
                unit_price=0.0,
                quantity=qty,
                subtotal=0.0,
                discount_pct=0.0,
                rush_premium_pct=0.0,
                notes="Out of stock / Unavailable" if is_unfulfillable else "Manual pricing required",
            ))
            continue

        unit_price = match["unit_price"]
        discount = _volume_discount(qty)
        final_price = unit_price * (1 - discount) * (1 + rush_premium)
        subtotal = round(final_price * qty, 2)

        line_pricing.append(LinePrice(
            line_item_index=i,
            unit_price=unit_price,
            quantity=qty,
            subtotal=subtotal,
            discount_pct=discount,
            rush_premium_pct=rush_premium,
            notes=f"Lead time: {match['lead_time_days']} days",
        ))
        total_confidence += match["confidence"]

    subtotal = round(sum(lp["subtotal"] for lp in line_pricing), 2)
    item_count = len(state.get("line_items", []))
    avg_confidence = round(total_confidence / item_count, 2) if item_count else 0.0

    logger.info(f"[PRICING] Total: {subtotal} | Confidence: {avg_confidence}")
    return {
        "line_pricing": line_pricing,
        "subtotal": subtotal,
        "total": subtotal,
        "pricing_confidence": avg_confidence,
    }
