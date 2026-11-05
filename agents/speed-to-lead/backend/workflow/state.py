from typing import TypedDict


class LeadState(TypedDict):
    # ── Inbound message ───────────────────────────────────────────────────────
    phone: str
    wa_name: str | None
    message_text: str | None
    message_type: str
    wa_message_id: str | None
    referral: dict | None

    # ── Firm context ──────────────────────────────────────────────────────────
    firm_id: str | None
    firm_vertical: str | None           # interior | real_estate | solar
    firm_display_name: str | None       # injected into prompts
    firm_visit_cta: str | None          # "Experience Center visit" etc.
    firm_meta_access_token: str | None  # for sending WA replies
    firm_contact_phone: str | None      # injected into prompts; other operational facts in knowledge base
    firm_contact_email: str | None

    # ── Agent routing ─────────────────────────────────────────────────────────
    path_taken: str | None

    # ── Lead identity ─────────────────────────────────────────────────────────
    lead_id: str | None
    lead_status: str
    ai_paused: bool
    broker_id: str | None               # channel partner who owns this lead, if any
    project_id: str | None              # project the lead is tied to
    escalation_reason: str | None       # negotiation | availability, set when routed to a human

    # ── CTWA context ──────────────────────────────────────────────────────────
    ctwa_source_id: str | None
    ctwa_config: str | None
    ctwa_location: str | None

    # ── Session ───────────────────────────────────────────────────────────────
    session_id: str | None
    lead_name: str | None

    # ── Qualification (shared fields, meaning varies by vertical) ─────────────
    # Interior/RE: config = flat config (2BHK); budget_bracket = cost bracket; scope = full_home/specific_room
    # Solar:       config = system size (3kW); budget_bracket = monthly bill bracket; scope = property type
    config: str | None
    budget_bracket: str | None
    scope: str | None

    # ── Interior-specific ─────────────────────────────────────────────────────
    design_style: str | None

    # ── Real Estate-specific ──────────────────────────────────────────────────
    cab_pickup_address: str | None

    # ── Solar-specific ────────────────────────────────────────────────────────
    roof_ownership: str | None          # owned | rented
    location_city: str | None
    subsidy_eligible: bool

    # ── Qualification gate ────────────────────────────────────────────────────
    is_qualified: bool
    disqualified_reason: str | None

    # ── Conversation state ────────────────────────────────────────────────────
    stage: str
    education_path: bool
    turn_count: int
    topics_covered: list[str]
    resources_shared: list[str]
    last_resource_turn: int

    # ── Lead capture flags ────────────────────────────────────────────────────
    name_captured: bool
    config_captured: bool
    budget_captured: bool
    visit_date_captured: bool

    # ── Booking ───────────────────────────────────────────────────────────────
    visit_date: str | None
    visit_time_slot: str | None

    # ── Visit action ──────────────────────────────────────────────────────────
    visit_action: str | None
    new_visit_date: str | None
    new_visit_time: str | None

    # ── History ───────────────────────────────────────────────────────────────
    history: list[dict]
    reactivated: bool

    # ── Response ──────────────────────────────────────────────────────────────
    is_knowledge_question: bool
    resource_explicitly_requested: bool
    response_text: str | None
    resource_to_attach: dict | None
    handoff_to_staff: bool

    # ── Observability ─────────────────────────────────────────────────────────
    knowledge_top_score: float | None
    knowledge_chunks: list[dict] | None
    portfolio_matches: list[dict] | None
    tools_called: list[str]
    claude_latency_ms: int | None
    pinecone_latency_ms: int | None
    total_latency_ms: int | None


def default_state(phone: str, wa_name: str | None = None) -> LeadState:
    return LeadState(
        phone=phone,
        wa_name=wa_name,
        message_text=None,
        message_type="text",
        wa_message_id=None,
        referral=None,
        firm_id=None,
        firm_vertical=None,
        firm_display_name=None,
        firm_visit_cta=None,
        firm_meta_access_token=None,
        firm_contact_phone=None,
        firm_contact_email=None,
        path_taken=None,
        lead_id=None,
        lead_status="new",
        ai_paused=False,
        broker_id=None,
        project_id=None,
        escalation_reason=None,
        ctwa_source_id=None,
        ctwa_config=None,
        ctwa_location=None,
        session_id=None,
        lead_name=None,
        config=None,
        budget_bracket=None,
        scope=None,
        design_style=None,
        cab_pickup_address=None,
        roof_ownership=None,
        location_city=None,
        subsidy_eligible=False,
        is_qualified=False,
        disqualified_reason=None,
        stage="discovery",
        education_path=False,
        turn_count=0,
        topics_covered=[],
        resources_shared=[],
        last_resource_turn=-1,
        name_captured=False,
        config_captured=False,
        budget_captured=False,
        visit_date_captured=False,
        visit_date=None,
        visit_time_slot=None,
        visit_action=None,
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
