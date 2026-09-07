import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from workflow.state import RFQState, FeasibilityResult
from models.gemini_models import get_gemini
from models.structured_output import FeasibilityReport
from prompts.rfq_prompts import FEASIBILITY_PROMPT

logger = logging.getLogger(__name__)

_llm = get_gemini()
_structured_llm = _llm.with_structured_output(FeasibilityReport)


def feasibility_node(state: RFQState) -> dict:
    logger.info(f"[FEASIBILITY] RFQ {state['rfq_id']} — checking {len(state.get('line_items', []))} items")

    payload = json.dumps({
        "line_items": state.get("line_items", []),
        "catalog_matches": state.get("catalog_matches", []),
        "rfq_deadline": state.get("rfq_deadline"),
        "delivery_location": state.get("delivery_location"),
    }, indent=2)

    try:
        result: FeasibilityReport = _structured_llm.invoke([
            SystemMessage(content=FEASIBILITY_PROMPT),
            HumanMessage(content=payload),
        ])
        items = result.items
    except Exception as e:
        logger.error(f"[FEASIBILITY] Failed for RFQ {state['rfq_id']}: {e}")
        items = []

    feasibility = [FeasibilityResult(
        line_item_index=item.line_item_index,
        feasible=item.feasible,
        reason=item.reason,
        alternative=item.alternative,
    ) for item in items]

    unfulfillable = [item.line_item_index for item in items if not item.feasible]
    logger.info(f"[FEASIBILITY] {len(unfulfillable)} unfulfillable items")

    return {
        "feasibility": feasibility,
        "unfulfillable_items": unfulfillable,
    }
