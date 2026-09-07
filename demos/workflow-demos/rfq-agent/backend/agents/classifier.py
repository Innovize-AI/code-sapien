import logging
from langchain_core.messages import SystemMessage, HumanMessage

from workflow.state import RFQState
from models.gemini_models import get_gemini
from models.structured_output import RFQClassification
from prompts.rfq_prompts import CLASSIFIER_PROMPT

logger = logging.getLogger(__name__)

_llm = get_gemini()
_structured_llm = _llm.with_structured_output(RFQClassification)


def classify_node(state: RFQState) -> dict:
    logger.info(f"[CLASSIFIER] RFQ {state['rfq_id']} — classifying urgency + complexity")

    summary = f"""
Line items count: {len(state.get('line_items', []))}
Deadline: {state.get('rfq_deadline')}
Missing fields: {state.get('missing_fields')}
Sample items: {state.get('line_items', [])[:3]}
"""
    try:
        result: RFQClassification = _structured_llm.invoke([
            SystemMessage(content=CLASSIFIER_PROMPT),
            HumanMessage(content=f"Classify this RFQ:\n{summary}"),
        ])
    except Exception as e:
        logger.error(f"[CLASSIFIER] Failed for RFQ {state['rfq_id']}: {e}")
        return {"urgency": "standard", "complexity": "review", "category": "unknown"}

    logger.info(f"[CLASSIFIER] urgency={result.urgency} complexity={result.complexity} category={result.category}")
    return {
        "urgency": result.urgency,
        "complexity": result.complexity,
        "category": result.category,
    }
