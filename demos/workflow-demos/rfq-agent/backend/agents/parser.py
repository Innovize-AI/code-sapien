import logging
from langchain_core.messages import SystemMessage, HumanMessage

from workflow.state import RFQState
from models.gemini_models import get_gemini
from models.structured_output import ParsedRFQ
from prompts.rfq_prompts import PARSER_PROMPT

logger = logging.getLogger(__name__)

_llm = get_gemini()
_structured_llm = _llm.with_structured_output(ParsedRFQ)


def parse_node(state: RFQState) -> dict:
    logger.info(f"[PARSER] RFQ {state['rfq_id']} — extracting line items")
    try:
        result: ParsedRFQ = _structured_llm.invoke([
            SystemMessage(content=PARSER_PROMPT),
            HumanMessage(content=f"Parse this RFQ:\n\n{state['raw_content']}"),
        ])
    except Exception as e:
        logger.error(f"[PARSER] Failed for RFQ {state['rfq_id']}: {e}")
        return {"error": f"Parser failed: {e}", "line_items": [], "missing_fields": [], "special_instructions": []}

    line_items = [item.model_dump() for item in result.line_items]
    logger.info(f"[PARSER] Extracted {len(line_items)} line items")

    return {
        "document_type": result.document_type,
        "rfq_type": result.rfq_type,
        "buyer_name": result.buyer_name,
        "buyer_contact": result.buyer_contact,
        "delivery_location": result.delivery_location,
        "rfq_deadline": result.rfq_deadline,
        "missing_fields": result.missing_fields,
        "special_instructions": result.special_instructions or [],
        "line_items": line_items,
    }
