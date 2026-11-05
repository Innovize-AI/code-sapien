"""
Gemini service — generation + embeddings.

Replaces the previous Anthropic implementation with identical function signatures
so no caller code needs to change.

Model: gemini-2.5-flash
Embeddings: Google text-embedding-004
Package: google-genai  (import: from google import genai)
"""

import asyncio
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Literal

from config import settings

log = logging.getLogger(__name__)

_MODEL        = "gemini-2.5-flash"
_MODEL_STRUCT = "gemini-2.5-flash"
_client: genai.Client | None = None


def init() -> None:
    global _client
    _client = genai.Client(api_key=settings.google_api_key)
    log.info("Gemini client initialised — model=%s", _MODEL)


def _client_or_raise() -> genai.Client:
    if _client is None:
        raise RuntimeError("claude.init() not called")
    return _client


# ── Structured output schemas ─────────────────────────────────────────────────

class SignalExtraction(BaseModel):
    lead_name: str | None = Field(None, description="Lead's first name or full name if stated")
    config: str | None = Field(
        None,
        description=(
            "For RE/ID: flat config '2BHK', '3BHK', '4BHK', 'Villa'. "
            "For solar: system size '1kW', '3kW', '5kW', '10kW', '10kW+'."
        ),
    )
    budget: str | None = Field(None, description="Budget for RE/ID in lakhs or crores e.g. '15 lakhs', '1.5 crore'")
    scope: Literal["full_home", "specific_room"] | None = Field(
        None, description="'full_home' if full renovation, 'specific_room' if only kitchen/bedroom/etc."
    )
    lead_type: Literal["interior", "real_estate", "solar"] | None = Field(
        None,
        description=(
            "'interior' for interior design, 'real_estate' for property purchase, "
            "'solar' for rooftop solar panel installation"
        ),
    )
    # Solar-specific fields
    property_type: Literal["residential", "commercial", "industrial"] | None = Field(
        None, description="Solar only: 'residential' for home, 'commercial' for office/shop, 'industrial' for factory"
    )
    monthly_bill: str | None = Field(
        None, description="Solar only: monthly electricity bill in Rs e.g. '3000', '5k', '8000'"
    )
    roof_ownership: Literal["owned", "rented"] | None = Field(
        None, description="Solar only: 'owned' if they own the property, 'rented' if it's a rented premises"
    )
    location_city: str | None = Field(
        None, description="Solar only: city or area for installation availability check"
    )
    visit_date: str | None = Field(
        None,
        description=(
            "Resolved visit/survey date in YYYY-MM-DD. Compute from today's date and the lead's expression "
            "('this Saturday', 'next Thursday', '15th'). Null if not mentioned."
        ),
    )
    visit_time: str | None = Field(None, description="Time mentioned for visit/survey e.g. '11am', 'morning'. Capture verbatim.")
    cab_pickup_address: str | None = Field(None, description="Pickup area or landmark for RE site visit cab")
    wants_resource: bool = Field(False, description="True if lead explicitly asked for a document, PDF, brochure, or video")
    is_knowledge_question: bool = Field(
        False,
        description=(
            "True if the lead is asking a substantive question about pricing, projects, process, "
            "scope, timeline, savings, subsidy, or any detail. False for short replies, names, dates, 'ok', 'thanks'."
        ),
    )
    education_path: bool = Field(
        False,
        description=(
            "True if the lead signals they are completely unfamiliar with interior design — "
            "e.g. 'I don't know where to start', 'just got keys', 'bare shell flat', "
            "'never done interior before', 'what do you do', 'kuch samajh nahi'."
        ),
    )


class VisitActionExtraction(BaseModel):
    action: Literal["cancel", "reschedule"] | None = Field(
        None,
        description=(
            "'cancel' if the lead clearly wants to cancel their visit. "
            "'reschedule' if they want to move to a different date/time. "
            "None if the message is unrelated to the existing booking."
        ),
    )
    new_date: str | None = Field(
        None,
        description="If rescheduling and a new date is mentioned, resolve to YYYY-MM-DD. Null otherwise.",
    )
    new_time: str | None = Field(
        None,
        description="New time slot if mentioned, e.g. '3pm', 'morning'.",
    )


class StageAssessment(BaseModel):
    stage: Literal["discovery", "qualification", "portfolio_match", "consideration", "booking", "conversion"] = Field(
        default="discovery",
        description=(
            "Updated stage — can only advance, never go back. "
            "discovery→qualification: lead asked a real question. "
            "qualification→portfolio_match: config and budget both known. "
            "portfolio_match→consideration: lead reacted to portfolio. "
            "consideration→booking: lead wants to visit. "
            "booking→conversion: visit date confirmed."
        ),
    )
    visit_intent_detected: bool = Field(default=False, description="True if lead expressed clear interest in visiting")


# ── Internal helpers ──────────────────────────────────────────────────────────

import re as _re

def _strip_json_markdown(text: str | None) -> str:
    """Extract the JSON object/array from Gemini output, stripping any preamble or markdown."""
    if not text:
        return "{}"
    # Try to find a JSON object or array in the text
    m = _re.search(r"(\{.*\}|\[.*\])", text, _re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: strip fences only
    text = text.strip()
    text = _re.sub(r"^```(?:json)?\s*", "", text)
    text = _re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_contents(history: list[dict] | None, user_message: str) -> list[types.Content]:
    """Convert Anthropic-style history + current message into Gemini Contents."""
    contents: list[types.Content] = []
    for h in (history or []):
        role = "model" if h["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    return contents


def _gen_config(
    max_tokens: int,
    temperature: float,
    system: str,
    schema: type[BaseModel] | None = None,
    no_thinking: bool = False,
) -> types.GenerateContentConfig:
    cfg: dict = {
        "system_instruction": system,
        "max_output_tokens": max_tokens,
        "temperature": temperature,
    }
    if schema is not None:
        cfg["response_mime_type"] = "application/json"
        cfg["response_schema"] = schema
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    elif no_thinking:
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**cfg)


# ── Text generation ───────────────────────────────────────────────────────────

async def generate_reply(
    system_prompt: str,
    user_message: str,
    history: list[dict] | None = None,
) -> str:
    client = _client_or_raise()
    response = await client.aio.models.generate_content(
        model=_MODEL,
        contents=_build_contents(history, user_message),
        config=_gen_config(1024, 0.3, system_prompt, no_thinking=True),
    )
    return response.text


def _today_ist() -> str:
    """Today's date in India, spelled out. Without it the model guesses the year and resolves
    'this Saturday' to a date in the past."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    return now.strftime("%A, %d %B %Y")


async def extract_signals(message: str, context_hint: str = "") -> dict:
    client = _client_or_raise()
    system = (
        "Extract structured lead information from the message below. "
        "Return only what is clearly stated — do not infer or guess. "
        f"Today is {_today_ist()} (India). Resolve any visit date relative to today and "
        "always to a date in the future. "
        f"{f'Context: {context_hint}' if context_hint else ''}"
    )
    try:
        response = await client.aio.models.generate_content(
            model=_MODEL_STRUCT,
            contents=message,
            config=_gen_config(512, 0.0, system, schema=SignalExtraction),
        )
        result = SignalExtraction.model_validate_json(_strip_json_markdown(response.text))
    except Exception as exc:
        log.warning("extract_signals failed: %s", exc)
        result = SignalExtraction()

    return {k: v for k, v in result.model_dump().items() if v is not None and v is not False}


async def extract_visit_action(message: str, booked_date: str) -> VisitActionExtraction:
    client = _client_or_raise()
    system = (
        f"The lead has an existing site visit booked on {booked_date}. "
        "Determine if their message is requesting a cancellation or reschedule."
    )
    try:
        response = await client.aio.models.generate_content(
            model=_MODEL,
            contents=message,
            config=_gen_config(256, 0.0, system, schema=VisitActionExtraction),
        )
        return VisitActionExtraction.model_validate_json(response.text)
    except Exception as exc:
        log.warning("extract_visit_action failed: %s", exc)
        return VisitActionExtraction()


async def assess_stage(
    message: str,
    current_stage: str,
    config: str | None,
    budget_bracket: str | None,
    turn_count: int,
    topics_covered: list[str],
    visit_date_captured: bool,
    response_text: str,
    system_override: str | None = None,
) -> StageAssessment:
    client = _client_or_raise()
    prompt = (
        f"Current stage: {current_stage}\n"
        f"Config known: {config or 'no'}\n"
        f"Budget known: {budget_bracket or 'no'}\n"
        f"Turn: {turn_count}\n"
        f"Topics covered: {', '.join(topics_covered) or 'none'}\n"
        f"Visit date captured: {visit_date_captured}\n"
        f"Lead said: {message}\n"
        f"Agent replied: {response_text[:200]}"
    )
    system = system_override or "Assess the conversation stage after this exchange. Stage can only advance, never go back."
    try:
        response = await client.aio.models.generate_content(
            model=_MODEL_STRUCT,
            contents=prompt,
            config=_gen_config(
                256, 0.0,
                system,
                schema=StageAssessment,
            ),
        )
        return StageAssessment.model_validate_json(_strip_json_markdown(response.text))
    except Exception as exc:
        log.warning("assess_stage failed: %s", exc)
        return StageAssessment(stage=current_stage)  # type: ignore[arg-type]


# ── Embeddings ────────────────────────────────────────────────────────────────

async def embed_query(text: str) -> list[float]:
    from google.genai import types as _gtypes
    client = _client_or_raise()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text,
                config=_gtypes.EmbedContentConfig(output_dimensionality=768),
            ),
        )
        return result.embeddings[0].values
    except Exception as exc:
        log.warning("embed_query failed: %s — returning zero vector", exc)
        return [0.0] * 768


async def embed_documents(texts: list[str]) -> list[list[float]]:
    from google.genai import types as _gtypes
    client = _client_or_raise()
    try:
        loop = asyncio.get_event_loop()
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), 100):
            batch = texts[i: i + 100]
            result = await loop.run_in_executor(
                None,
                lambda b=batch: client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=b,
                    config=_gtypes.EmbedContentConfig(output_dimensionality=768),
                ),
            )
            all_embeddings.extend(e.values for e in result.embeddings)
        return all_embeddings
    except Exception as exc:
        log.warning("embed_documents failed: %s", exc)
        return [[0.0] * 768 for _ in texts]
