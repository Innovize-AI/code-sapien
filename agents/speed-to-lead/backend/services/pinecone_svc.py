"""
Pinecone service — knowledge, portfolio, and resource search.

Namespaces are vertical-prefixed:
  {vertical}-knowledge  — chunked docs for pricing, process, FAQs, project details
  {vertical}-portfolio  — project metadata + image refs for portfolio matching
  {vertical}-resources  — file metadata (PDFs + YouTube links) for resource gate

  Special case: solar portfolio uses "solar-case-studies" instead of "solar-portfolio".

Search thresholds:
  knowledge  >= 0.80 -> use; < 0.80 -> fallback
  portfolio  >= 0.75 -> return matches
  resources  >= 0.70 -> attach

Embedding: Google text-embedding-004 via claude.embed_query (keeps index compatible).
Ingestion: raw Pinecone upsert (no LangChain dependency).
"""

import asyncio
import logging
import time

from pinecone import Pinecone

from config import settings

log = logging.getLogger(__name__)

KNOWLEDGE_THRESHOLD = 0.80
PORTFOLIO_THRESHOLD = 0.75
RESOURCE_THRESHOLD  = 0.70

_index = None

# Per-firm resource catalogue cache: firm_id -> list[dict]
_resource_catalogue: dict[str, list[dict]] = {}


def _ns(firm_id: str, kind: str) -> str:
    """Return the Pinecone namespace for a given firm and content kind."""
    return f"{firm_id}-{kind}"


def init() -> None:
    global _index
    index_name = settings.pinecone_index_name
    log.info("Pinecone connecting — index=%s environment=%s", index_name, settings.environment)
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(index_name)
        stats = _index.describe_index_stats()
        log.info(
            "Pinecone initialised — index=%s vectors=%d",
            index_name, stats.total_vector_count,
        )
    except Exception as exc:
        log.warning("Pinecone init failed (index=%s): %s — search disabled", index_name, exc)
        _index = None


async def load_resource_catalogue(db, firm_id: str | None = None) -> None:
    """Load resource catalogue for a specific firm (or all firms if firm_id is None)."""
    global _resource_catalogue
    try:
        from db.crud import list_resources
        rows = await list_resources(db, firm_id=firm_id)
        catalogue_entries = [
            {
                "id":            r.id,
                "title":         r.title or "",
                "description":   r.description or "",
                "resource_type": r.resource_type or "pdf",
                "url":           r.url or "",
                "firm_id":       str(r.firm_id) if r.firm_id else None,
            }
            for r in rows
        ]
        if firm_id:
            _resource_catalogue[firm_id] = catalogue_entries
            log.info("Resource catalogue loaded for firm=%s — %d resources", firm_id, len(catalogue_entries))
        else:
            # Group by firm_id
            from collections import defaultdict
            grouped: dict[str, list] = defaultdict(list)
            for entry in catalogue_entries:
                fid = entry.get("firm_id") or "__global__"
                grouped[fid].append(entry)
            for fid, entries in grouped.items():
                _resource_catalogue[fid] = entries
            log.info("Resource catalogue loaded — %d total resources across %d firms", len(catalogue_entries), len(grouped))
    except Exception as exc:
        log.error("Failed to load resource catalogue: %s", exc)


def get_resource_catalogue(firm_id: str | None = None) -> list[dict]:
    if firm_id and firm_id in _resource_catalogue:
        return _resource_catalogue[firm_id]
    # Fallback: return all catalogued resources flattened
    all_resources = []
    for entries in _resource_catalogue.values():
        all_resources.extend(entries)
    return all_resources


def get_resource_catalogue_text(firm_id: str | None = None) -> str | None:
    catalogue = get_resource_catalogue(firm_id)
    if not catalogue:
        return None
    lines = ["Available resources (use ID to attach):"]
    for r in catalogue:
        lines.append(f"  [{r['id']}] {r['title']} ({r['resource_type']})")
    return "\n".join(lines)


def get_resource_by_id(resource_id: str, firm_id: str | None = None) -> dict | None:
    catalogue = get_resource_catalogue(firm_id)
    return next((r for r in catalogue if r["id"] == resource_id), None)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _embed(text: str) -> list[float]:
    from services.claude import embed_query
    return await embed_query(text)


def _query(vec: list[float], namespace: str, k: int, filter: dict | None = None) -> list:
    try:
        kwargs: dict = dict(vector=vec, top_k=k, namespace=namespace, include_metadata=True)
        if filter:
            kwargs["filter"] = filter
        result = _index.query(**kwargs)
        return result.matches
    except Exception as exc:
        log.error("Pinecone query failed namespace=%s: %s", namespace, exc)
        return []


# ── Knowledge search ──────────────────────────────────────────────────────────

async def search_knowledge(query: str, firm_id: str = "", vertical: str = "interior") -> dict:
    """
    Search knowledge namespace for the given firm. Returns:
      matches: list of {id, score, text, source, doc_type}
      pinecone_latency_ms
    """
    if not _index:
        return {"matches": [], "pinecone_latency_ms": 0}

    namespace = _ns(firm_id, "knowledge") if firm_id else f"{vertical}-knowledge"
    t = time.monotonic()

    vec = await _embed(query)
    if not vec:
        return {"matches": [], "pinecone_latency_ms": 0}

    raw = await asyncio.to_thread(_query, vec, namespace, 5)
    latency_ms = int((time.monotonic() - t) * 1000)

    matches = [
        {
            "id":       m.id,
            "score":    round(m.score, 4),
            "text":     m.metadata.get("text", ""),
            "source":   m.metadata.get("source", ""),
            "doc_type": m.metadata.get("doc_type", ""),
        }
        for m in raw
    ]

    log.info(
        "search_knowledge vertical=%s query=%r top_score=%.4f latency=%dms",
        vertical, query[:60], matches[0]["score"] if matches else 0.0, latency_ms,
    )
    return {"matches": matches, "pinecone_latency_ms": latency_ms}


# ── Portfolio search ──────────────────────────────────────────────────────────

async def search_portfolio(
    query: str,
    config: str | None = None,
    budget_bracket: str | None = None,
    vertical: str = "interior",
    firm_id: str = "",
) -> dict:
    """
    Search portfolio namespace for the given firm. Returns top 2 matching projects.
    Optionally filters by config/budget_bracket metadata.
    """
    if not _index:
        return {"matches": [], "pinecone_latency_ms": 0}

    namespace = _ns(firm_id, "portfolio") if firm_id else f"{vertical}-portfolio"
    t = time.monotonic()

    vec = await _embed(query)
    if not vec:
        return {"matches": [], "pinecone_latency_ms": 0}

    filter_: dict = {}
    if config:
        filter_["config"] = {"$eq": config}
    if budget_bracket:
        filter_["budget_bracket"] = {"$eq": budget_bracket}

    raw = await asyncio.to_thread(_query, vec, namespace, 2, filter_ or None)

    # If filtered search returned nothing, retry without filters
    if not raw and filter_:
        raw = await asyncio.to_thread(_query, vec, namespace, 2, None)

    latency_ms = int((time.monotonic() - t) * 1000)

    matches = [
        {
            "id":            m.id,
            "score":         round(m.score, 4),
            "title":         m.metadata.get("title", ""),
            "location":      m.metadata.get("location", ""),
            "config":        m.metadata.get("config", ""),
            "budget_bracket":m.metadata.get("budget_bracket", ""),
            "style":         m.metadata.get("style", ""),
            "image_urls":    m.metadata.get("image_urls", []),
            "brochure_url":  m.metadata.get("brochure_url"),
            "description":   m.metadata.get("description", ""),
            "vertical":      m.metadata.get("vertical", ""),
        }
        for m in raw
    ]

    log.info(
        "search_portfolio vertical=%s query=%r top_score=%.4f latency=%dms",
        vertical, query[:60], matches[0]["score"] if matches else 0.0, latency_ms,
    )
    return {"matches": matches, "pinecone_latency_ms": latency_ms}


# ── Resource search ───────────────────────────────────────────────────────────

async def search_resources(query: str, vertical: str = "interior", firm_id: str = "") -> dict | None:
    """Search resources namespace for the given firm. Returns top match metadata or None."""
    if not _index:
        return None

    namespace = _ns(firm_id, "resources") if firm_id else f"{vertical}-resources"

    vec = await _embed(query)
    if not vec:
        return None

    raw = await asyncio.to_thread(_query, vec, namespace, 1, None)
    if not raw:
        return None

    m = raw[0]
    return {"id": m.id, "score": round(m.score, 4), **m.metadata}


# ── Ingestion helpers (used by seed scripts) ──────────────────────────────────

async def upsert_knowledge(docs: list[dict], firm_id: str = "", vertical: str = "interior") -> None:
    """
    Upsert knowledge chunks.
    Each dict: {id, text, source, doc_type}
    """
    if not _index:
        return

    namespace = _ns(firm_id, "knowledge") if firm_id else f"{vertical}-knowledge"

    from services.claude import embed_documents
    texts = [d["text"] for d in docs]
    vectors = await embed_documents(texts)

    records = [
        {
            "id":       d["id"],
            "values":   v,
            "metadata": {k: d[k] for k in ("text", "source", "doc_type") if k in d},
        }
        for d, v in zip(docs, vectors)
    ]
    await asyncio.to_thread(_index.upsert, records, namespace=namespace)
    log.info("Upserted %d knowledge chunks to namespace=%s", len(records), namespace)


async def upsert_portfolio(projects: list[dict], firm_id: str = "", vertical: str = "interior") -> None:
    """
    Upsert portfolio projects.
    Each dict: {id, title, description, location, config, budget_bracket, style,
                image_urls, brochure_url}
    The embedded text is title + description.
    """
    if not _index:
        return

    namespace = _ns(firm_id, "portfolio") if firm_id else f"{vertical}-portfolio"

    from services.claude import embed_documents
    texts = [f"{p['title']}. {p.get('description', '')}".strip(". ") for p in projects]
    vectors = await embed_documents(texts)

    records = [
        {
            "id":       p["id"],
            "values":   v,
            "metadata": {
                k: p.get(k, "") for k in (
                    "title", "description", "location", "config",
                    "budget_bracket", "style", "brochure_url",
                )
            } | {"image_urls": p.get("image_urls", [])},
        }
        for p, v in zip(projects, vectors)
    ]
    await asyncio.to_thread(_index.upsert, records, namespace=namespace)
    log.info("Upserted %d portfolio projects to namespace=%s", len(records), namespace)


async def upsert_resources(resources: list[dict], firm_id: str = "", vertical: str = "interior") -> None:
    """
    Upsert resource metadata.
    Each dict: {id, title, description, resource_type, url}
    """
    if not _index:
        return

    namespace = _ns(firm_id, "resources") if firm_id else f"{vertical}-resources"

    from services.claude import embed_documents
    texts = [f"{r['title']}. {r.get('description', '')}".strip(". ") for r in resources]
    vectors = await embed_documents(texts)

    records = [
        {
            "id":       r["id"],
            "values":   v,
            "metadata": {k: r.get(k, "") for k in ("title", "description", "resource_type", "url")},
        }
        for r, v in zip(resources, vectors)
    ]
    await asyncio.to_thread(_index.upsert, records, namespace=namespace)
    log.info("Upserted %d resources to namespace=%s", len(records), namespace)
