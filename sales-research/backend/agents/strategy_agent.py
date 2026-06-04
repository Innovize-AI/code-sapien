from models.structured_output_cso import MultiOutreachSequence
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from datetime import datetime
from prompts.sales_prompts import (
    PAIN_POINT_DISCOVERY_PROMPT,
    STRATEGIC_SOLUTION_PROMPT,
    OUTREACH_DESIGN_PROMPT
)
import json
from models.structured_output import OutreachStrategy, Solution, StrategicSolutions
from models.structured_output_cso import OutreachSequence
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


# No global knowledge_service - must be resolved per-request

def format_profile_analysis(analysis: dict) -> str:
    """Helper to convert structured LinkedInAnalysis dict to markdown string for LLM prompts."""
    # ... (existing content)
    if not analysis or not isinstance(analysis, dict):
        return str(analysis)
    
    md = f"""
PROFILE SUMMARY:
{analysis.get('profile_summary', 'N/A')}

STRATEGIC ROLE FIT:
{analysis.get('strategic_role_fit', 'N/A')}

COMPANY SIGNALS:
{analysis.get('company_signals', 'N/A')}

ENGAGEMENT PERSONA:
{analysis.get('engagement_persona', 'N/A')}

PAIN POINT HYPOTHESIS:
{analysis.get('pain_point_hypothesis', 'N/A')}

RECENT POSTS:
"""
    for post in analysis.get('posts_analysis', []):
        md += f"- {post.get('post_title')} ({post.get('posted_date')}): {post.get('summary')} [URL: {post.get('post_url')}]\n"
    
    return md

def format_website_analysis(analysis: dict) -> str:
    """Helper to convert structured WebsiteAnalysis dict to markdown string for LLM prompts."""
    if not analysis or not isinstance(analysis, dict):
        return str(analysis)
        
    md = f"""
OVERVIEW:
{analysis.get('summary', 'N/A')}

INDUSTRY:
{analysis.get('industry', 'N/A')}

TARGET AUDIENCE:
{analysis.get('target_audience', 'N/A')}

OFFERINGS:
{", ".join(analysis.get('core_offerings', []))}

INDUSTRY PAIN POINTS:
{", ".join(analysis.get('industry_pain_points', []))}

COMPETITIVE ADVANTAGE:
{analysis.get('competitive_advantage', 'N/A')}
"""
    return md


class PainPointAnalysis(BaseModel):
    summary: str = Field(description="High-level overview of identified challenges.")
    points: List[str] = Field(description="Specific, individual pain points discovered.")
    impact: str = Field(description="The potential business impact if these are not addressed.")

class StrategicSolutionProposal(BaseModel):
    summary: str = Field(description="Overview of the proposed transformation.")
    solutions: List[Solution] = Field(description="Specific AI/Service solutions proposed with Logical Gap Mapping.")
    value_proposition: str = Field(description="The core value delivered by these solutions.")

def pain_point_node(state: AgentState):
    """Identifies specific, actionable pain points from the lead's profile and company footprint."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)
    website_analysis_dict = state.get("website_analysis", {})
    website_analysis = format_website_analysis(website_analysis_dict)
    hiring_data = state.get("hiring_data", [])
    company_news = state.get("company_news", [])
    company_stats = state.get("company_stats", {})
    
    prompt = PAIN_POINT_DISCOVERY_PROMPT.format(
        user_analysis=user_analysis,
        website_analysis=website_analysis,
        hiring_data=json.dumps(hiring_data),
        company_news=json.dumps(company_news),
        company_stats=json.dumps(company_stats)
    )

    messages = [
        SystemMessage(content="You are an expert business analyst specializing in B2B pain point identification. You look for deeper organizational struggles, not just surface issues."),
        HumanMessage(content=prompt)
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(PainPointAnalysis)
        response = structured_llm.invoke(messages)
        return {"target_pain_points": response.model_dump() if response else {}}
    except Exception as e:
        logger.error(f"Error in pain_point_node: {e}")
        return {"target_pain_points": {}}


def strategic_solution_synthesizer_node(state: AgentState):
    """
    Synthesizes the research_solution_pool into the structured strategic_solutions field.
    This ensures the frontend receives the data in the high-fidelity format it expects.
    """
    solution_pool = state.get("research_solution_pool", [])
    if isinstance(solution_pool, str):
        try:
            solution_pool = json.loads(solution_pool)
        except:
            solution_pool = []

    if isinstance(solution_pool, dict):
        try:
            sorted_keys = sorted(solution_pool.keys(), key=lambda x: int(x) if str(x).isdigit() else x)
            solution_pool = [solution_pool[k] for k in sorted_keys]
        except:
            solution_pool = list(solution_pool.values())

    normalized_pool = []
    if isinstance(solution_pool, list):
        for p in solution_pool:
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except:
                    pass
            if isinstance(p, dict):
                normalized_pool.append(p)
    solution_pool = normalized_pool

    if not solution_pool:
        logger.info("Synthesizer: No research solution pool found. Skipping.")
        return {"strategic_solutions": []}

    target_pain_points = state.get("target_pain_points", {})
    selling_profile = state.get("selling_company_profile")
    selling_company_name = getattr(selling_profile, "company_name", "Our Company") if selling_profile else "Our Company"
    business_model = getattr(selling_profile, "business_model", "product") if selling_profile else "product"
    
    # Context summary for the prompt
    selling_company_context = f"Business Model: {business_model}"
    
    # We pass the entire pool as the context
    pool_str = ""
    for idx, p in enumerate(solution_pool):
        if not isinstance(p, dict): continue
        pool_str += f"\nPRODUCT {idx+1}: {p.get('product_name')}\n"
        pool_str += f"TECHNICAL: {p.get('technical_intel')}\n"
        pool_str += f"NARRATIVE: {p.get('narrative_intel')}\n"
        pool_str += f"COLLATERAL: {p.get('collateral_intel')}\n"
        pool_str += f"OBJECTIONS: {p.get('objections')}\n"

    prompt = STRATEGIC_SOLUTION_PROMPT.format(
        pain_points=json.dumps(target_pain_points),
        lead_segment=state.get("lead_segment", "POTENTIAL_CLIENT"),
        selling_company_name=selling_company_name,
        business_model=business_model,
        selling_company_context=selling_company_context,
        solution_context=pool_str
    )

    messages = [
        SystemMessage(content="You are a Strategic Solution Architect. Your mission is to map RAG intelligence to specific prospect pain points with high-fidelity 'Logical Gap Mapping'."),
        HumanMessage(content=prompt)
    ]

    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(StrategicSolutions)
        response = structured_llm.invoke(messages)
        
        if not response or not response.solutions:
            return {"strategic_solutions": []}
            
        # Convert to list of dicts for state/persistence
        solutions_list = [s.model_dump() for s in response.solutions]
        logger.info(f"Synthesizer: Successfully generated {len(solutions_list)} strategic solutions.")
        return {"strategic_solutions": solutions_list}
        
    except Exception as e:
        logger.error(f"Error in strategic_solution_synthesizer_node: {e}", exc_info=True)
        return {"strategic_solutions": []}



def _extract_templates_from_rag(rag_briefing: str) -> list:
    """
    Parses strategic_rag_briefing and extracts per-step email templates.

    The RAG briefing wraps each Pinecone chunk as:
        --- [Source: <file> | ... | Relevance: 0.xx] ---
        [H1 > H2 > STEP_TYPE -- angle]

        template body with [INJECT:] slots

    So we split on chunk boundaries and detect step templates by breadcrumb keywords.
    Falls back to legacy ### header parsing for raw (non-briefing-wrapped) content.
    """
    import re

    if not rag_briefing:
        return []

    # Pull the NARRATIVE/MESSAGING block
    narrative = rag_briefing
    if "NARRATIVE/MESSAGING:" in rag_briefing:
        after = rag_briefing.split("NARRATIVE/MESSAGING:", 1)[1]
        for end_marker in ["COLLATERAL/PROOF:", "OBJECTIONS:", "SOURCES/PLAYBOOKS:", "TECHNICAL:"]:
            if end_marker in after:
                after = after.split(end_marker, 1)[0]
        narrative = after.strip()

    if not narrative or "[INJECT:" not in narrative:
        return []

    STEP_KEYWORDS = ("LI_INVITE", "EMAIL_DIRECT", "EMAIL_FOLLOWUP", "BREAK_UP_EMAIL", "LI_COMMENT")

    # Method 1: RAG briefing chunk format — split on "--- [Source:" separators
    # Each chunk breadcrumb contains the step type e.g. "> EMAIL_DIRECT -- surface_the_gap"
    raw_chunks = re.split(r'-{3,}\s*\[Source:', narrative)
    step_chunks = []
    for chunk in raw_chunks:
        if not chunk.strip():
            continue
        breadcrumb_match = re.search(r'\[([^\]]+)\]', chunk)
        if breadcrumb_match:
            breadcrumb = breadcrumb_match.group(1)
            if any(kw in breadcrumb for kw in STEP_KEYWORDS) and "[INJECT:" in chunk:
                step_chunks.append(chunk.strip())

    if step_chunks:
        return step_chunks

    # Method 2: Legacy raw format — split on ### step headers
    step_prefixes = (
        "### EMAIL_DIRECT",
        "### EMAIL_FOLLOWUP",
        "### BREAK_UP_EMAIL",
        "### LI_INVITE",
        "### LI_COMMENT",
    )
    templates = []
    current_header = None
    current_lines = []
    for line in narrative.split("\n"):
        if line.strip().startswith(step_prefixes):
            if current_header and current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    templates.append(f"{current_header}\n{body}")
            current_header = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_header and current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            templates.append(f"{current_header}\n{body}")

    # Fallback: return whole section as one block
    if not templates and "[INJECT:" in narrative:
        templates = [narrative.strip()]

    return templates


def _build_template_section(playbook_examples: list, outreach_blueprints: list, lead_score: int, selected_product: str = "") -> str:
    """
    Builds the variant generation protocol for outreach_node.

    With templates:
      Variant 1 - Template-based: clones workflow template, fills [INJECT:] slots only.
      Variant 2 - Personalized: writes every step fresh from research signals.

    Without templates (no specific use case matched):
      Both variants are personalized but use different angles from the CSO blueprints.
    """
    v1 = outreach_blueprints[0] if len(outreach_blueprints) > 0 else {}
    v2 = outreach_blueprints[1] if len(outreach_blueprints) > 1 else {}
    v1_name = v1.get("variant_name", "Variant 1")
    v2_name = v2.get("variant_name", "Variant 2")

    lines = [
        "### VARIANT GENERATION PROTOCOL (MANDATORY):",
        "",
        "You MUST produce EXACTLY TWO sequences with fundamentally different writing approaches.",
        "",
    ]

    # ── No templates - both variants personalized ─────────────────────────────
    if not playbook_examples:
        lines += [
            "No workflow template is available for the selected use case.",
            "Both variants must be fully personalized - written from scratch using research signals.",
            "",
            f"=== SEQUENCE 1: \"{v1_name}\" - PERSONALIZED (Signal-Led) ===",
            "",
            "Angle: Lead with the strongest research signal - hiring role, company news, or post.",
            "Every paragraph must reference something specific about this company.",
            "",
        ]
        if v1.get("steps"):
            lines.append("Signals and intent per step:")
            for step in v1.get("steps", []):
                engagement = step.get("engagement_type", "")
                angle = step.get("narrative_angle", "")
                signal = step.get("reference_signal", "")
                note = step.get("internal_note", "")
                lines.append(f"  {engagement} [{angle}]")
                if signal:
                    lines.append(f"    Signal: {signal[:120]}")
                if note:
                    lines.append(f"    Intent: {note[:120]}")
            lines.append("")

        lines += [
            f"=== SEQUENCE 2: \"{v2_name}\" - PERSONALIZED (Pain-Led) ===",
            "",
            "Angle: Lead with the pain point. Open by naming the operational friction directly.",
            "Do not reference the same signal as Variant 1 - find a different entry point.",
            "",
        ]
        if v2.get("steps"):
            lines.append("Signals and intent per step:")
            for step in v2.get("steps", []):
                engagement = step.get("engagement_type", "")
                angle = step.get("narrative_angle", "")
                signal = step.get("reference_signal", "")
                note = step.get("internal_note", "")
                lines.append(f"  {engagement} [{angle}]")
                if signal:
                    lines.append(f"    Signal: {signal[:120]}")
                if note:
                    lines.append(f"    Intent: {note[:120]}")
            lines.append("")

        if lead_score >= 70:
            lines.append("Lead Score 70+ - invest in deep personalization on steps 1-3 for both variants.")
        elif lead_score >= 41:
            lines.append("Lead Score 41-69 - one strong signal per step is sufficient for both variants.")
        else:
            lines.append("Lead Score <40 - keep both variants brief.")

        return "\n".join(lines)

    # ── VARIANT 1: Template-based ─────────────────────────────────────────────
    lines += [
        f"=== SEQUENCE 1: \"{v1_name}\" - TEMPLATE-BASED ===",
        "",
        "Rule: For every EMAIL and LI_INVITE step, clone the matching template below.",
        "  - Find the template whose header matches the step's narrative_angle",
        "  - Copy the paragraph structure, sentence rhythm, and CTA style exactly",
        "  - Fill ONLY the [INJECT: ...] slots - do not rewrite the argument",
        "  - LI_COMMENT: always 100% fresh - write from the reference_signal post content",
        "",
    ]

    if playbook_examples:
        header = "TEMPLATES TO CLONE:"
        if selected_product:
            header += f" Selected workflow is '{selected_product}' — use only the templates whose ## section matches this workflow. Ignore all others."
        lines.append(header)
        lines.append("")
        for i, example in enumerate(playbook_examples, 1):
            lines.append(f"--- Template {i} ---")
            lines.append(example.strip())
            lines.append("")

        if v1.get("steps"):
            lines.append("Step injection map for this variant:")
            for step in v1.get("steps", []):
                engagement = step.get("engagement_type", "")
                angle = step.get("narrative_angle", "")
                signal = step.get("reference_signal", "")
                inject = signal[:100] if signal else "use primary pain point from CSO briefing"
                lines.append(f"  {engagement} [{angle}] -> inject: {inject}")
            lines.append("")
    else:
        lines.append("No templates found in playbook_examples - write Variant 1 using the CSO internal_notes as structure guide.")
        lines.append("")

    # ── VARIANT 2: Fully personalized ────────────────────────────────────────
    lines += [
        f"=== SEQUENCE 2: \"{v2_name}\" - FULLY PERSONALIZED ===",
        "",
        "Rule: Do NOT use any template from above. Write every step from scratch.",
        "  - Hook must reference a specific signal: hiring role, post, news, or website finding",
        "  - Argument must be built from the prospect's actual research - not generic pain framing",
        "  - CTA must tie back to their specific situation, not a generic 'worth a chat?'",
        "  - Each paragraph must contain at least one company-specific detail",
        "  - LI_COMMENT: write a genuine, insightful comment on their exact post",
        "",
    ]

    if v2.get("steps"):
        lines.append("Research signals to weave in for this variant:")
        for step in v2.get("steps", []):
            engagement = step.get("engagement_type", "")
            angle = step.get("narrative_angle", "")
            signal = step.get("reference_signal", "")
            note = step.get("internal_note", "")
            lines.append(f"  {engagement} [{angle}]")
            if signal:
                lines.append(f"    Signal: {signal[:120]}")
            if note:
                lines.append(f"    Intent: {note[:120]}")
        lines.append("")

    # Lead score context applies to both
    if lead_score >= 70:
        lines.append("Lead Score 70+ - both variants should invest in strong personalization on steps 1-3.")
    elif lead_score >= 41:
        lines.append("Lead Score 41-69 - Variant 1 template injection is sufficient. Variant 2 should go deeper on signals.")
    else:
        lines.append("Lead Score <40 - keep both variants brief. Do not over-invest in research depth.")

    return "\n".join(lines)


def outreach_node(state: AgentState):
    """Crafts the personalized "hook" and outbound message using structured output."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)

    # Context from CSO
    cso_briefing = state.get("cso_strategic_briefing", {})
    selected_product = cso_briefing.get("selected_product_name", "Our Solution")

    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")

    selling_profile = state.get("selling_company_profile")

    # Extract lookalike_peer from CSO briefing
    lookalike_peer = cso_briefing.get("lookalike_peer", "N/A")

    # Extract hiring_data from state
    hiring_data = state.get("hiring_data", [])
    if isinstance(hiring_data, str):
        try:
            hiring_data = json.loads(hiring_data)
        except:
            logger.warning("Strategy Agent: Could not parse hiring_data string as JSON")
            hiring_data = []

    prompt = OUTREACH_DESIGN_PROMPT.format(
        user_analysis=user_analysis,
        lead_segment=lead_segment,
        lookalike_peer=lookalike_peer,
        solutions=f"PRODUCT SELECTED BY CSO: {selected_product}\nJUSTIFICATION: {cso_briefing.get('selected_product_justification')}",
        hiring_data=json.dumps(hiring_data),
        cso_context=json.dumps(cso_briefing),
        current_date=datetime.now().strftime("%A, %B %d, %Y")
    )

    # Add RAG Instruction (The "Winning Intel" passed from CSO)
    rag_briefing = state.get("strategic_rag_briefing", "No RAG context available.")
    prompt += f"""
### STRATEGIC RAG BRIEFING (THE WINNING INTEL):
{rag_briefing}
"""

    # Extract templates directly from the NARRATIVE/MESSAGING section of strategic_rag_briefing
    # (more reliable than playbook_examples which CSO summarises into short snippets)
    rag_briefing = state.get("strategic_rag_briefing", "")
    extracted_templates = _extract_templates_from_rag(rag_briefing)
    outreach_blueprints = cso_briefing.get("outreach_sequences", [])
    lead_score = state.get("lead_score_analysis", {}).get("total_score", 50)
    if isinstance(lead_score, str):
        try:
            lead_score = int(lead_score)
        except:
            lead_score = 50

    template_section = _build_template_section(extracted_templates, outreach_blueprints, lead_score, selected_product)
    if template_section:
        prompt += f"\n{template_section}\n"

    validation_feedback = state.get("outreach_validation_feedback")
    existing_sequences = state.get("final_outreach_sequences") or state.get("personalized_outreach")

    if validation_feedback and existing_sequences:
        logger.info(f"Strategy Agent: Running in selective adjustment mode. Feedback: {validation_feedback}")
        prompt = f"""You are a world-class Direct Response Copywriter. You need to adjust the existing outreach sequences based on the validation feedback.

### EXISTING SEQUENCES:
{json.dumps(existing_sequences, indent=2)}

### VALIDATION FEEDBACK:
{json.dumps(validation_feedback, indent=2)}

### REGULATED PRODUCT INTEL & CONTEXT (FOR GROUNDING REFINE DRAFTS):
PRODUCT SELECTED BY CSO: {selected_product}
JUSTIFICATION: {cso_briefing.get('selected_product_justification')}
LOOKALIKE PEER: {lookalike_peer}
RAG BRIEFING: {rag_briefing}

### INSTRUCTIONS FOR REVISION (STRICT):
1. Review the validation feedback. It specifies which sequence variant name and which step number failed deliverability check, along with the issue and suggestion.
2. For all sequences and steps that have NO issues (i.e. not mentioned in the step_feedbacks list), you MUST copy their values (`variant_name`, `primary_pain_point`, `sequence_theme`, `engagement_type`, `delay_days`, `trigger`, `narrative_angle`, `reference_signal`, `internal_note`, `draft`, `email_subject`, `subject_line_variants`, `preview_text`, `ps_line`, `cta_type`, `sources`, etc.) EXACTLY VERBATIM. Do not alter even a single character.
3. For the specific steps that DID receive feedback, rewrite ONLY those steps to address the issues listed in the feedback.
4. When rewriting the drafts, maintain the original strategy, context, and intent. Ensure they are grounded in the product/RAG briefing and do not introduce spam words, capitalization in email subjects, or 'P.S.' prefix in the `ps_line`.
5. Return the full set of sequences containing both the unchanged steps and the adjusted steps.
"""
    else:
        validation_feedback = None

    messages = [
        SystemMessage(content="""You are a world-class Direct Response Copywriter and Strategic Sales Consultant. 
        Your mission is to craft outreach that is authentic, evidence-based, and completely free of generic AI terminology.
        You rely strictly on the provided 'Strategic RAG Briefing' to ground your claims.
        """),
        HumanMessage(content=prompt)
    ]

    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0.2)
        # The Outreach Designer takes the CSO's Blueprints and returns the fully populated Sequences
        structured_llm = model.with_structured_output(MultiOutreachSequence)
        response = structured_llm.invoke(messages)
        
        if not response or not response.sequences:
            logger.warning("Strategy Agent: Model returned empty or null sequences. Check CSO context and prompt grounding.")
            return {
                "final_outreach_sequences": [],
                "personalized_outreach": [], 
                "campaign_outreach_variants": []
            }
        
        all_sequences_dict = [s.model_dump() for s in response.sequences]

        # Merge with existing sequences if we are in selective adjustment/refinement mode
        if validation_feedback and existing_sequences:
            existing_by_name = {seq.get("variant_name"): seq for seq in existing_sequences if seq.get("variant_name")}
            updated_by_name = {seq.get("variant_name"): seq for seq in all_sequences_dict if seq.get("variant_name")}
            
            merged_sequences = []
            for var_name, existing_seq in existing_by_name.items():
                if var_name in updated_by_name:
                    merged_sequences.append(updated_by_name[var_name])
                else:
                    merged_sequences.append(existing_seq)
            for var_name, updated_seq in updated_by_name.items():
                if var_name not in existing_by_name:
                    merged_sequences.append(updated_seq)
            all_sequences_dict = merged_sequences

        # Tag each sequence so the frontend knows which approach was used
        has_templates = bool(extracted_templates)
        for i, seq in enumerate(all_sequences_dict):
            if not has_templates:
                seq["outreach_approach"] = "personalized_signal" if i == 0 else "personalized_pain"
            elif i == 0:
                seq["outreach_approach"] = "template_based"
            else:
                seq["outreach_approach"] = "personalized"

        logger.info(f"Strategy Agent: Generated {len(all_sequences_dict)} sequences - approaches: {[s['outreach_approach'] for s in all_sequences_dict]}")

        return {
            "final_outreach_sequences": all_sequences_dict,
            "personalized_outreach": all_sequences_dict,
        }
        
    except Exception as e:
        logger.error(f"Error in outreach_node: {e}", exc_info=True)
        return {
            "final_outreach_sequences": [],
            "personalized_outreach": [],
        }


# ─── Outreach Validator (ReAct Agent) ────────────────────────────────────────

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

SPAM_WORDS = {"free", "guarantee", "earn $", "act now", "urgent", "click here", "special offer", "100% results"}

@tool
def scan_step_deliverability(engagement_type: str, subject: str, draft: str, ps_line: str) -> str:
    """
    Check a single outreach step for deliverability and tone issues.
    Returns a list of specific failures found, or PASS if clean.
    """
    issues = []

    # Double P.S. check
    if ps_line and ps_line.strip().upper().startswith("P.S"):
        issues.append(f"{engagement_type}: ps_line starts with 'P.S.' - platform prepends it automatically, this will render as 'P.S. P.S. ...'")

    # Spam word check (subject + draft)
    combined = f"{subject} {draft}".lower()
    found_spam = [w for w in SPAM_WORDS if w in combined]
    if found_spam:
        issues.append(f"{engagement_type}: spam trigger words found - {found_spam}")

    # Rigid structure check
    rigid_patterns = ["problem:", "solution:", "result:", "benefit:", "feature:"]
    if any(p in draft.lower() for p in rigid_patterns):
        issues.append(f"{engagement_type}: rigid colon-label structure detected (e.g. 'Problem: ...'). Use flowing paragraphs.")

    # Bullet block check - 3+ consecutive bullet lines
    bullet_lines = [l for l in draft.split("\n") if l.strip().startswith(("-", "-", "->", "*", "[x]"))]
    if len(bullet_lines) >= 3:
        issues.append(f"{engagement_type}: {len(bullet_lines)} consecutive bullet lines - reads like a feature list, not a human email.")

    # CRM reference check (first-touch emails only)
    if engagement_type in ("EMAIL_DIRECT", "LI_INVITE", "LI_DM"):
        crm_refs = ["hubspot", "salesforce", "netsuite", "pipedrive", "zoho crm"]
        found_crm = [c for c in crm_refs if c in draft.lower()]
        if found_crm:
            issues.append(f"{engagement_type}: CRM platform names in first-touch copy - {found_crm}. Remove unless required by the specific workflow.")

    # Subject line check (emails only)
    if engagement_type in ("EMAIL_DIRECT", "EMAIL_FOLLOWUP", "BREAK_UP_EMAIL"):
        if subject and len(subject.split()) > 7:
            issues.append(f"{engagement_type}: subject line too long ({len(subject.split())} words). Keep it 3-7 words.")
        if subject and subject != subject.lower():
            issues.append(f"{engagement_type}: subject line has capitalisation - should be lowercase for deliverability.")

    # Em-dash check
    if "—" in draft or (subject and "—" in subject) or (ps_line and "—" in ps_line):
        issues.append(f"{engagement_type}: contains em-dash ('—'). Em-dashes are banned. Use commas, parentheses, or normal punctuation instead.")
    if "--" in draft or (subject and "--" in subject) or (ps_line and "--" in ps_line):
        issues.append(f"{engagement_type}: contains double hyphen ('--'). Double hyphens are banned. Use commas, parentheses, or normal punctuation instead.")

    return "PASS" if not issues else "\n".join(issues)


@tool
def check_variant_differentiation(v1_hook: str, v2_hook: str) -> str:
    """
    Check whether the two variants have meaningfully different opening hooks.
    v1_hook and v2_hook should be the first 2 sentences of the EMAIL_DIRECT step from each variant.
    Returns DIFFERENT or TOO_SIMILAR with a reason.
    """
    v1_lower = v1_hook.lower().strip()
    v2_lower = v2_hook.lower().strip()

    if not v1_lower or not v2_lower:
        return "SKIP - one or both hooks are empty, cannot compare."

    # Simple similarity: if first 40 chars are identical, they're the same template copy
    if v1_lower[:40] == v2_lower[:40]:
        return "TOO_SIMILAR: Both variants open with the same sentence. Variant 2 must start from a different angle entirely."

    # Word overlap check - >70% shared words suggests copy-paste with light edits
    v1_words = set(v1_lower.split())
    v2_words = set(v2_lower.split())
    if len(v1_words) > 0:
        overlap = len(v1_words & v2_words) / len(v1_words)
        if overlap > 0.7:
            return f"TOO_SIMILAR: {int(overlap*100)}% word overlap in hooks. Variant 2 needs a genuinely different entry point."

    return "DIFFERENT - hooks are distinct enough for A/B testing."


class StepFeedback(BaseModel):
    sequence_variant_name: str = Field(description="Name of the sequence variant (e.g. 'Variant 1' or 'Scaling Friction Focus')")
    step_number: int = Field(description="Step number (1-indexed)")
    engagement_type: str = Field(description="Step type, e.g. EMAIL_DIRECT, LI_DM, etc.")
    issue: str = Field(description="Specific feedback/issue found for this step")
    suggestion: str = Field(description="Specific rewrite/adjustment suggestion for this step")


@tool
def submit_verdict(is_safe: bool, step_feedbacks: List[StepFeedback], global_feedback: Optional[str] = None) -> str:
    """
    Submit the final validation verdict. Call this ONCE after checking all steps.
    is_safe: True only if every check passed for both variants.
    step_feedbacks: List of feedback items for steps that failed validation. Empty list if safe.
    global_feedback: Overall differentiation or structural issues, if any.
    """
    return f"Verdict recorded - is_safe={is_safe}, issues={len(step_feedbacks)}"


_VALIDATOR_AGENT = None

def _get_validator_agent():
    global _VALIDATOR_AGENT
    if _VALIDATOR_AGENT is None:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        _VALIDATOR_AGENT = create_react_agent(
            model=model,
            tools=[scan_step_deliverability, check_variant_differentiation, submit_verdict],
            prompt="""You are a strict outreach deliverability judge. Your job is to validate two outreach sequence variants before they are sent to prospects.

WHAT TO CHECK:
1. Call scan_step_deliverability for EVERY email and LinkedIn step in BOTH variants.
   - Pass: engagement_type, subject (or empty string), draft body, ps_line (or empty string).
2. Call check_variant_differentiation using the first 2 sentences of EMAIL_DIRECT from each variant.
3. If any step fails or if differentiation fails, collect detailed feedback for ALL failing sequences and steps.
4. After checking everything, call submit_verdict with your final decision.
   - If is_safe is False, populate the `step_feedbacks` list with a detailed feedback item for each specific step of each sequence that failed validation. Include the sequence variant name (e.g. 'Variant 1' or 'Scaling Friction Focus'), step number, engagement type, the scan issues, and a clear suggestion for rewriting that specific step.
   - If differentiation check fails, also provide a global_feedback entry explaining the differentiation issue.

PASS criteria (all must be true):
- Every scan_step_deliverability call returned PASS
- check_variant_differentiation returned DIFFERENT
- No step sounds like a template that forgot to fill its [INJECT:] slots

FAIL criteria (any one is enough to fail):
- Any deliverability issue found in any step
- Variants are too similar
- A draft still contains literal [INJECT: ...] placeholder text

Call submit_verdict exactly once at the end with your complete findings. Be thorough and make sure to list feedback for all failing steps."""
        )
    return _VALIDATOR_AGENT


async def outreach_validator_node(state: AgentState) -> dict:
    """ReAct-based validator. Checks both outreach variants before passing to report_generator."""
    sequences = state.get("final_outreach_sequences") or []
    attempts = state.get("outreach_attempts") or 0

    if isinstance(sequences, dict):
        sequences = [sequences]

    if not sequences:
        logger.warning("Validator: No sequences to validate - skipping.")
        return {"outreach_validation_feedback": None, "outreach_attempts": attempts}

    # Format sequences for the agent
    formatted = []
    for idx, seq in enumerate(sequences):
        formatted.append(f"\n=== SEQUENCE {idx+1} ({seq.get('variant_name', f'variant_{idx+1}')}) ===")
        for step in seq.get("steps", []):
            formatted.append(
                f"step_number: {step.get('step_number')}\n"
                f"engagement_type: {step.get('engagement_type', '')}\n"
                f"subject: {step.get('email_subject', '')}\n"
                f"draft: {step.get('draft', '')}\n"
                f"ps_line: {step.get('ps_line', '')}\n"
            )

    human_msg = "Validate the following outreach sequences:\n" + "\n---\n".join(formatted)

    try:
        agent = _get_validator_agent()
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=human_msg)]},
            config={"recursion_limit": 4}
        )

        # Extract verdict from submit_verdict tool call in message history
        is_safe = True
        step_feedbacks = []
        global_feedback = ""

        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    if tc["name"] == "submit_verdict":
                        args = tc.get("args", {})
                        is_safe = args.get("is_safe", True)
                        raw_sf = args.get("step_feedbacks", [])
                        step_feedbacks = []
                        for sf in raw_sf:
                            if isinstance(sf, dict):
                                step_feedbacks.append(sf)
                            elif hasattr(sf, "model_dump"):
                                step_feedbacks.append(sf.model_dump())
                        global_feedback = args.get("global_feedback", "")
                        break

        logger.info(f"Validator: is_safe={is_safe}, issues={len(step_feedbacks)}, attempt={attempts}")

        if not is_safe:
            return {
                "outreach_validation_feedback": {
                    "step_feedbacks": step_feedbacks,
                    "global_feedback": global_feedback
                },
                "outreach_attempts": attempts + 1
            }

        return {"outreach_validation_feedback": None, "outreach_attempts": attempts}

    except Exception as e:
        logger.error(f"Validator error: {e}", exc_info=True)
        return {"outreach_validation_feedback": None, "outreach_attempts": attempts}

