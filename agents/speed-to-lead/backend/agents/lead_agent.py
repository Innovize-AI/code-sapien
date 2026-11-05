"""
Lead agent node — main conversation handler.

Architecture: pre-fetch -> context injection -> single Claude call.
  1. If is_knowledge_question:
       a. Stage is portfolio_match OR message has style/project keywords -> search portfolio
       b. Otherwise (or portfolio below threshold) -> search knowledge
       c. Below KNOWLEDGE_THRESHOLD -> fallback (pause AI + alert staff)
  2. Build system prompt with retrieved context injected
  3. Single claude.generate_reply() call
  4. Resource gate: maybe attach a PDF/video to the reply
"""

import asyncio
import logging
import smtplib
import time
from email.message import EmailMessage

from workflow.state import LeadState
from services import claude, pinecone_svc
from services import resource_gate as rg
from prompts.lead_agent_prompts import build_system_prompt, get_fallback_message
from agents.tools import KNOWLEDGE_THRESHOLD, PORTFOLIO_THRESHOLD, _db_ctx
from agents.escalation import REPLIES as ESCALATION_REPLIES, detect_escalation

log = logging.getLogger(__name__)

import re as _re_facts

_FACT_TOPICS = _re_facts.compile(
    r"\b(rera|possession|handover|hand over|ready to move|price|pricing|cost|rate|rates|"
    r"payment plan|payment|loan|bank|banks|emi|how much)\b",
    _re_facts.IGNORECASE,
)

_PORTFOLIO_KEYWORDS = {
    "project", "work", "portfolio", "done", "similar", "example", "photo", "image",
    "photos", "images", "style", "design", "look", "modern", "classic", "contemporary",
    "luxury", "show", "see", "reference", "inspiration", "sample", "idea", "previous",
}


async def lead_agent_node(state: LeadState) -> LeadState:
    message = state.get("message_text") or ""
    history = state.get("history", [])
    stage = state.get("stage", "discovery")
    vertical = state.get("firm_vertical") or "interior"
    firm_id = state.get("firm_id")

    # ── Audio guard ───────────────────────────────────────────────────────────
    if state.get("message_type") == "audio":
        state["response_text"] = "Can you send that as a text? Can't process voice notes here."
        state["path_taken"] = "voice_note"
        state["tools_called"] = []
        return state

    # ── Escalation: negotiation and unit availability always go to a person ───
    reason = detect_escalation(message)
    if reason:
        state["escalation_reason"] = reason
        state["path_taken"] = "escalation"
        state["response_text"] = ESCALATION_REPLIES[reason]
        state["handoff_to_staff"] = True
        state["tools_called"] = []
        asyncio.create_task(_alert_team(state))
        return state

    t0 = time.monotonic()
    retrieved_context = ""
    path = "conversational"
    resources_shared = state.get("resources_shared", [])

    # ── Project facts: price, RERA, possession, payment plan, loans ──────────
    # These are stored on the project record and quoted exactly. A question about them is
    # answered from the record, so it never falls back to a human for lack of a document.
    facts = None
    try:
        from services.broker_registry import project_facts_text
        facts = await project_facts_text(_db_ctx.get(), firm_id, state.get("project_id"))
    except LookupError:
        pass
    use_facts = bool(facts) and bool(_FACT_TOPICS.search(message))
    if use_facts:
        retrieved_context = facts
        path = "project_facts"

    # ── Context retrieval ─────────────────────────────────────────────────────
    if state.get("is_knowledge_question") and not use_facts:
        want_portfolio = (
            stage in ("portfolio_match", "consideration")
            or any(kw in message.lower() for kw in _PORTFOLIO_KEYWORDS)
        )

        if want_portfolio:
            port_result = await pinecone_svc.search_portfolio(
                query=message,
                config=state.get("config"),
                budget_bracket=state.get("budget_bracket"),
                vertical=vertical,
                firm_id=firm_id or "",
            )
            port_matches = port_result.get("matches", [])
            state["portfolio_matches"] = port_matches
            if state.get("pinecone_latency_ms") is None:
                state["pinecone_latency_ms"] = port_result.get("pinecone_latency_ms")

            top_score = port_matches[0]["score"] if port_matches else 0.0
            if top_score >= PORTFOLIO_THRESHOLD:
                state["knowledge_top_score"] = top_score
                retrieved_context = _format_portfolio(port_matches)
                path = "portfolio"

        if not retrieved_context:
            know_result = await pinecone_svc.search_knowledge(message, firm_id=firm_id or "", vertical=vertical)
            know_matches = know_result.get("matches", [])
            state["pinecone_latency_ms"] = know_result.get("pinecone_latency_ms")
            top_score = know_matches[0]["score"] if know_matches else 0.0
            state["knowledge_top_score"] = top_score
            state["knowledge_chunks"] = know_matches

            if top_score < KNOWLEDGE_THRESHOLD:
                # In booking/conversion the lead is asking logistics questions
                # (timing, pickup, availability) — the LLM can answer these from
                # the system prompt's operational facts. Only hard-fallback for
                # earlier stages where hallucinating project details is risky.
                if stage in ("booking", "conversion"):
                    retrieved_context = ""
                    path = "conversational"
                else:
                    state["path_taken"] = "fallback"
                    state["response_text"] = get_fallback_message(vertical)
                    state["handoff_to_staff"] = True
                    state["tools_called"] = []
                    asyncio.create_task(_alert_team(state))
                    return state

            retrieved_context = _format_knowledge(know_matches)
            path = "knowledge"
            _update_topics(state, know_matches)

    # ── Build system prompt ───────────────────────────────────────────────────
    catalogue = pinecone_svc.get_resource_catalogue(firm_id=firm_id) or []

    system = build_system_prompt(state, resource_catalogue=catalogue if catalogue else None)

    if retrieved_context:
        system += f"\n\n--- RETRIEVED CONTEXT ---\n{retrieved_context}"

    # Project facts (RERA number, possession date, price, payment plan) are quoted exactly
    if facts:
        system += f"\n\n--- PROJECT FACTS (quote exactly, never invent) ---\n{facts}"

    # ── Generate reply ────────────────────────────────────────────────────────
    response_text = await claude.generate_reply(system, message, history)
    state["claude_latency_ms"] = int((time.monotonic() - t0) * 1000)
    state["path_taken"] = path
    state["tools_called"] = [path] if path != "conversational" else []

    # ── Resource gate (LLM-decided, DWPS pattern) ─────────────────────────────
    clean_text, resource_id = _parse_resource_tag(response_text or "")
    state["response_text"] = clean_text

    if resource_id and catalogue:
        resource = _resolve_resource(resource_id, catalogue)
        if resource:
            explicit = state.get("resource_explicitly_requested", False)
            attach, gate_fail = rg.should_attach(state, resource, explicit=explicit)
            if attach:
                state["resource_to_attach"] = {
                    "id":    resource["id"],
                    "type":  resource.get("resource_type", "pdf"),
                    "url":   resource.get("url", ""),
                    "title": resource.get("title", ""),
                }
                state["resources_shared"] = resources_shared + [resource["id"]]
                state["last_resource_turn"] = state.get("turn_count", 0)
                log.info("RESOURCE ATTACHED — id=%s type=%s", resource["id"], resource.get("resource_type"))
            else:
                log.debug("Resource gate blocked — id=%s reason=%s", resource_id, gate_fail)
        else:
            log.warning("LLM chose unknown resource_id=%r — ignoring", resource_id)

    return state


# ── Resource tag helpers (DWPS pattern) ──────────────────────────────────────

import re as _re

_RESOURCE_TAG_RE = _re.compile(r"\[RESOURCE:\s*([^\]]+)\]\s*$", _re.MULTILINE)


def _parse_resource_tag(text: str) -> tuple[str, str | None]:
    """Strip [RESOURCE: <id>] tag from LLM reply. Returns (clean_text, resource_id | None)."""
    m = _RESOURCE_TAG_RE.search(text)
    if not m:
        return text, None
    resource_id = m.group(1).strip()
    clean = _RESOURCE_TAG_RE.sub("", text).rstrip()
    return clean, resource_id


def _resolve_resource(resource_id: str, catalogue: list[dict]) -> dict | None:
    """Look up a resource by id from the in-memory catalogue list."""
    for r in catalogue:
        if r.get("id") == resource_id:
            return r
    return None


# ── Formatting helpers ────────────────────────────────────────────────────────

def _format_portfolio(matches: list[dict]) -> str:
    lines = []
    for m in matches:
        lines.append(f"PROJECT: {m['title']}")
        if m.get("location"):   lines.append(f"  Location: {m['location']}")
        if m.get("config"):     lines.append(f"  Config: {m['config']}")
        if m.get("style"):      lines.append(f"  Style: {m['style']}")
        if m.get("budget_bracket"): lines.append(f"  Budget range: {m['budget_bracket']}")
        if m.get("description"): lines.append(f"  About: {m['description']}")
        if m.get("image_urls"): lines.append(f"  Images: {', '.join(m['image_urls'][:3])}")
        if m.get("brochure_url"): lines.append(f"  Brochure: {m['brochure_url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_knowledge(matches: list[dict]) -> str:
    return "\n\n".join(
        f"[{m.get('doc_type', 'knowledge')}] {m['text']}"
        for m in matches if m.get("text")
    )


def _update_topics(state: LeadState, matches: list[dict]) -> None:
    topics = state.get("topics_covered", [])
    for m in matches:
        dt = m.get("doc_type", "")
        if dt and dt not in topics:
            topics = topics + [dt]
    state["topics_covered"] = topics


# ── Fallback alert ────────────────────────────────────────────────────────────

async def _alert_team(state: LeadState) -> None:
    from config import settings
    # Use firm-level fallback email if available, else global setting
    alert_email = state.get("firm_meta_access_token")  # placeholder — firms table has fallback_alert_email
    if not settings.fallback_alert_email:
        return

    reason = state.get("escalation_reason")
    subject = (f"[Speed-to-Lead] {reason.capitalize()} question: {state.get('phone', 'unknown')}"
               if reason else f"[Speed-to-Lead] Unanswered query: {state.get('phone', 'unknown')}")
    lead_in = (f"The buyer asked about {reason}. This is routed to a person by design.\n"
               if reason else "The AI could not answer with sufficient confidence.\n")
    body = (
        lead_in +
        f"AI has been PAUSED for this lead. Please respond manually on WhatsApp.\n\n"
        f"Phone: {state.get('phone')}\n"
        f"Lead name: {state.get('lead_name') or 'unknown'}\n"
        f"Vertical: {state.get('firm_vertical') or 'unknown'}\n"
        f"Firm: {state.get('firm_display_name') or 'unknown'}\n"
        f"Message: {state.get('message_text')}\n"
        f"Pinecone score: {state.get('knowledge_top_score')}\n"
        f"Stage: {state.get('stage')}\n"
        f"Turn: {state.get('turn_count')}\n\n"
        f"Re-enable AI from the dashboard -> Leads -> AI Paused.\n"
    )

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = settings.fallback_alert_email
        msg.set_content(body)

        def _send():
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
                s.starttls()
                s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)

        await asyncio.to_thread(_send)
    except Exception as exc:
        log.warning("Fallback alert email failed: %s", exc)
