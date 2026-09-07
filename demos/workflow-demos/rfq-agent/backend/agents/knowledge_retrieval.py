import logging
from workflow.state import RFQState, CatalogMatch
from services.catalog_service import query_catalog

logger = logging.getLogger(__name__)


def retrieve_node(state: RFQState) -> dict:
    logger.info(f"[RETRIEVAL] RFQ {state['rfq_id']} — querying catalog for {len(state.get('line_items', []))} items")
    matches: list[CatalogMatch] = []

    for i, item in enumerate(state.get("line_items", [])):
        query = f"{item['description']} {item.get('specs', '')}".strip()
        results = query_catalog(query, top_k=3)

        if results:
            best = results[0]
            matches.append(CatalogMatch(
                line_item_index=i,
                product_id=best["product_id"],
                product_name=best["product_name"],
                unit_price=best["unit_price"],
                available=best["available"],
                lead_time_days=best["lead_time_days"],
                confidence=best["score"],
                notes=best.get("notes"),
            ))
        else:
            matches.append(CatalogMatch(
                line_item_index=i,
                product_id="NOT_FOUND",
                product_name="No match found",
                unit_price=0.0,
                available=False,
                lead_time_days=0,
                confidence=0.0,
                notes="No catalog match — requires manual pricing",
            ))

    logger.info(f"[RETRIEVAL] Matched {sum(1 for m in matches if m['product_id'] != 'NOT_FOUND')}/{len(matches)} items")
    return {"catalog_matches": matches}
