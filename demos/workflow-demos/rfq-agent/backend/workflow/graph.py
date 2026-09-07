import logging
import inspect

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from workflow.state import RFQState
from agents.parser import parse_node
from agents.classifier import classify_node
from agents.knowledge_retrieval import retrieve_node
from agents.feasibility import feasibility_node
from agents.pricing import pricing_node
from agents.drafter import draft_node
from agents.dispatcher import dispatch_node, human_queue_node
from agents.freight import freight_node
from services import trace_store


def traced(node_fn, node_name: str):
    if inspect.iscoroutinefunction(node_fn):
        async def async_wrapper(state: RFQState):
            rfq_id = state.get("rfq_id", "")
            trace_store.emit(rfq_id, node_name, "running")
            try:
                result = await node_fn(state)
                trace_store.emit(rfq_id, node_name, "done")
                return result
            except Exception as e:
                trace_store.emit(rfq_id, node_name, "error", str(e))
                raise
        return async_wrapper
    else:
        def sync_wrapper(state: RFQState):
            rfq_id = state.get("rfq_id", "")
            trace_store.emit(rfq_id, node_name, "running")
            try:
                result = node_fn(state)
                trace_store.emit(rfq_id, node_name, "done")
                return result
            except Exception as e:
                trace_store.emit(rfq_id, node_name, "error", str(e))
                raise
        return sync_wrapper


def route_after_parse(state: RFQState) -> list[str]:
    """Fan out after parsing — freight skips catalog/feasibility/pricing."""
    if state.get("error"):
        logger.warning(f"RFQ {state['rfq_id']} parse failed: {state['error']}")
        return ["human_queue_node"]
    if state.get("rfq_type") == "freight":
        return ["freight_node"]
    return ["classify_node", "retrieve_node"]


def route_review(state: RFQState) -> str:
    """All quotes go to human review before dispatch."""
    return "human_queue_node"


def build_graph() -> StateGraph:
    builder = StateGraph(RFQState)

    builder.add_node("parse_node",       traced(parse_node,       "parse_node"))
    builder.add_node("classify_node",    traced(classify_node,    "classify_node"))
    builder.add_node("retrieve_node",    traced(retrieve_node,    "retrieve_node"))
    builder.add_node("feasibility_node", traced(feasibility_node, "feasibility_node"))
    builder.add_node("pricing_node",     traced(pricing_node,     "pricing_node"))
    builder.add_node("freight_node",     traced(freight_node,     "freight_node"))
    builder.add_node("draft_node",       traced(draft_node,       "drafter_node"))
    builder.add_node("dispatch_node",    traced(dispatch_node,    "dispatch_node"))
    builder.add_node("human_queue_node", traced(human_queue_node, "human_queue_node"))

    # Entry
    builder.add_edge(START, "parse_node")

    # Branch: freight → freight_node, product → classify + retrieve in parallel
    builder.add_conditional_edges(
        "parse_node",
        route_after_parse,
        ["classify_node", "retrieve_node", "freight_node", "human_queue_node"]
    )

    # Freight path: freight_node → draft_node (skips catalog/feasibility/pricing)
    builder.add_edge("freight_node", "draft_node")

    # Product path: classify + retrieve converge → feasibility → pricing → draft
    builder.add_edge("classify_node",    "feasibility_node")
    builder.add_edge("retrieve_node",    "feasibility_node")
    builder.add_edge("feasibility_node", "pricing_node")
    builder.add_edge("pricing_node",     "draft_node")

    # Review gate (shared by both paths)
    builder.add_conditional_edges(
        "draft_node",
        route_review,
        ["dispatch_node", "human_queue_node"]
    )

    builder.add_edge("dispatch_node",    END)
    builder.add_edge("human_queue_node", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
