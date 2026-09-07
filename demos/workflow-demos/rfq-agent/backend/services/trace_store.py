"""In-memory agent trace store for SSE streaming."""
import time
from typing import Optional
from collections import defaultdict

_store: dict[str, list[dict]] = defaultdict(list)
_subscribers: dict[str, list] = defaultdict(list)

NODE_META = {
    "parse_node":           ("Parsing RFQ",          "Extracting line items, buyer info, and requirements"),
    "classify_node":        ("Classifying",           "Determining urgency and complexity"),
    "retrieve_node":        ("Catalog search",        "Finding matching products in catalog"),
    "feasibility_node":     ("Feasibility check",     "Verifying supply availability"),
    "freight_node":         ("Freight parsing",       "Extracting transport requirements"),
    "pricing_node":         ("Pricing",               "Calculating unit prices and totals"),
    "freight_pricing_node": ("Freight pricing",       "Estimating transport cost"),
    "drafter_node":         ("Drafting quote",        "Generating professional quotation"),
    "dispatch_node":        ("Dispatching",           "Sending quote to buyer"),
    "human_queue_node":     ("Queued for review",     "Flagged for manual approval"),
}


def emit(rfq_id: str, node: str, status: str, detail: Optional[str] = None):
    label, default_detail = NODE_META.get(node, (node, ""))
    event = {
        "node": node,
        "label": label,
        "detail": detail or default_detail,
        "status": status,  # "running" | "done" | "error"
        "ts": time.time(),
    }
    _store[rfq_id].append(event)


def get_trace(rfq_id: str) -> list[dict]:
    return list(_store.get(rfq_id, []))


def clear(rfq_id: str):
    _store.pop(rfq_id, None)
