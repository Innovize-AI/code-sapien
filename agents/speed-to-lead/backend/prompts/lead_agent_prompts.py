"""
System prompts for the Speed-to-Lead agent.
Routes to the correct vertical prompt builder.

Backward-compat: lead_agent_system() is kept for any callers that haven't migrated yet.
New code should call build_system_prompt(state, resource_catalogue=...) instead.
"""

from __future__ import annotations

from workflow.state import LeadState


# ── Multi-vertical router (new API) ──────────────────────────────────────────

def build_system_prompt(state: LeadState, resource_catalogue: list[dict] | None = None) -> str:
    vertical = state.get("firm_vertical") or "interior"

    if vertical == "solar":
        from prompts.solar_prompts import build_system_prompt as _build
        return _build(
            lead_name=state.get("lead_name"),
            property_type=state.get("scope"),        # scope reused for property_type
            monthly_bill_bracket=state.get("budget_bracket"),
            system_size_kw=state.get("config"),       # config reused for system_size_kw
            roof_ownership=state.get("roof_ownership"),
            location_city=state.get("location_city"),
            subsidy_eligible=state.get("subsidy_eligible", False),
            stage=state.get("stage", "discovery"),
            turn_count=state.get("turn_count", 0),
            topics_covered=state.get("topics_covered", []),
            resources_shared=state.get("resources_shared", []),
            name_captured=state.get("name_captured", False),
            config_captured=state.get("config_captured", False),
            budget_captured=state.get("budget_captured", False),
            visit_date_captured=state.get("visit_date_captured", False),
            firm_display_name=state.get("firm_display_name") or "[Firm Name]",
            firm_visit_cta=state.get("firm_visit_cta") or "free site survey",
            resource_catalogue=resource_catalogue,
            visit_action=state.get("visit_action"),
            visit_date=state.get("visit_date"),
        )

    if vertical == "real_estate":
        from prompts.real_estate_prompts import build_system_prompt as _build
        return _build(
            lead_name=state.get("lead_name"),
            config=state.get("config"),
            budget_bracket=state.get("budget_bracket"),
            property_location=state.get("ctwa_location"),
            cab_pickup_address=state.get("cab_pickup_address"),
            stage=state.get("stage", "discovery"),
            turn_count=state.get("turn_count", 0),
            topics_covered=state.get("topics_covered", []),
            resources_shared=state.get("resources_shared", []),
            name_captured=state.get("name_captured", False),
            config_captured=state.get("config_captured", False),
            budget_captured=state.get("budget_captured", False),
            visit_date_captured=state.get("visit_date_captured", False),
            is_qualified=state.get("is_qualified", True),
            disqualified_reason=state.get("disqualified_reason"),
            education_path=state.get("education_path", False),
            firm_display_name=state.get("firm_display_name") or "[Firm Name]",
            firm_visit_cta=state.get("firm_visit_cta") or "site visit (cab arranged)",
            firm_contact_phone=state.get("firm_contact_phone"),
            firm_contact_email=state.get("firm_contact_email"),
            ctwa_config=state.get("ctwa_config"),
            ctwa_location=state.get("ctwa_location"),
            resource_catalogue=resource_catalogue,
            visit_action=state.get("visit_action"),
            visit_date=state.get("visit_date"),
        )

    # Default: interior
    from prompts.interior_prompts import build_system_prompt as _build
    return _build(
        lead_name=state.get("lead_name"),
        config=state.get("config"),
        budget_bracket=state.get("budget_bracket"),
        scope=state.get("scope"),
        design_style=state.get("design_style"),
        stage=state.get("stage", "discovery"),
        turn_count=state.get("turn_count", 0),
        topics_covered=state.get("topics_covered", []),
        resources_shared=state.get("resources_shared", []),
        name_captured=state.get("name_captured", False),
        config_captured=state.get("config_captured", False),
        budget_captured=state.get("budget_captured", False),
        visit_date_captured=state.get("visit_date_captured", False),
        education_path=state.get("education_path", False),
        firm_display_name=state.get("firm_display_name") or "[Firm Name]",
        firm_visit_cta=state.get("firm_visit_cta") or "Experience Center visit",
        ctwa_config=state.get("ctwa_config"),
        ctwa_location=state.get("ctwa_location"),
        resource_catalogue=resource_catalogue,
        visit_action=state.get("visit_action"),
        visit_date=state.get("visit_date"),
    )


def get_fallback_message(vertical: str | None) -> str:
    if vertical == "solar":
        from prompts.solar_prompts import FALLBACK_MESSAGE
        return FALLBACK_MESSAGE
    if vertical == "real_estate":
        from prompts.real_estate_prompts import FALLBACK_MESSAGE
        return FALLBACK_MESSAGE
    from prompts.interior_prompts import FALLBACK_MESSAGE
    return FALLBACK_MESSAGE


def get_stage_assessment_system(vertical: str | None) -> str:
    if vertical == "solar":
        from prompts.solar_prompts import STAGE_ASSESSMENT_SYSTEM
        return STAGE_ASSESSMENT_SYSTEM
    if vertical == "real_estate":
        from prompts.real_estate_prompts import STAGE_ASSESSMENT_SYSTEM
        return STAGE_ASSESSMENT_SYSTEM
    from prompts.interior_prompts import STAGE_ASSESSMENT_SYSTEM
    return STAGE_ASSESSMENT_SYSTEM


# ── Backward-compat single-function API (kept for migration safety) ───────────

def lead_agent_system(
    lead_name: str | None,
    config: str | None,
    budget_bracket: str | None,
    scope: str | None,
    lead_type: str | None,
    stage: str,
    turn_count: int,
    topics_covered: list[str],
    resources_shared: list[str],
    name_captured: bool,
    config_captured: bool,
    budget_captured: bool,
    visit_date_captured: bool,
    education_path: bool,
    ctwa_config: str | None = None,
    ctwa_location: str | None = None,
    resource_catalogue: str | None = None,
    visit_action: str | None = None,
    visit_date: str | None = None,
) -> str:
    """
    DEPRECATED: use build_system_prompt(state) instead.
    Kept for backward compatibility with callers that haven't migrated yet.
    """
    # Build a minimal state dict and route through the new system
    fake_state = LeadState(
        phone="",
        wa_name=None,
        message_text=None,
        message_type="text",
        wa_message_id=None,
        referral=None,
        firm_id=None,
        firm_vertical=lead_type or "interior",
        firm_display_name=None,
        firm_visit_cta=None,
        firm_meta_access_token=None,
        firm_contact_phone=None,
        firm_contact_email=None,
        path_taken=None,
        lead_id=None,
        lead_status="new",
        ai_paused=False,
        ctwa_source_id=None,
        ctwa_config=ctwa_config,
        ctwa_location=ctwa_location,
        session_id=None,
        lead_name=lead_name,
        config=config,
        budget_bracket=budget_bracket,
        scope=scope,
        design_style=None,
        cab_pickup_address=None,
        roof_ownership=None,
        location_city=None,
        subsidy_eligible=False,
        is_qualified=False,
        disqualified_reason=None,
        stage=stage,
        education_path=education_path,
        turn_count=turn_count,
        topics_covered=topics_covered,
        resources_shared=resources_shared,
        last_resource_turn=-1,
        name_captured=name_captured,
        config_captured=config_captured,
        budget_captured=budget_captured,
        visit_date_captured=visit_date_captured,
        visit_date=visit_date,
        visit_time_slot=None,
        visit_action=visit_action,
        new_visit_date=None,
        new_visit_time=None,
        history=[],
        reactivated=False,
        is_knowledge_question=False,
        resource_explicitly_requested=False,
        response_text=None,
        resource_to_attach=None,
        handoff_to_staff=False,
        knowledge_top_score=None,
        knowledge_chunks=None,
        portfolio_matches=None,
        tools_called=[],
        claude_latency_ms=None,
        pinecone_latency_ms=None,
        total_latency_ms=None,
    )
    return build_system_prompt(fake_state, resource_catalogue=resource_catalogue)


# ── Legacy constants (kept for any direct imports) ────────────────────────────

FALLBACK_MESSAGE = (
    "I don't have a confident answer for that — let me connect you with our team directly.\n\n"
    "You can reach us at [number] / [email]. They'll get back to you shortly."
)

STAGE_ASSESSMENT_SYSTEM = (
    "You assess conversation stages for a real estate and interior design lead agent. "
    "Stage can only advance forward, never go back. "
    "Stages: discovery -> qualification -> portfolio_match -> consideration -> booking -> conversion."
)
