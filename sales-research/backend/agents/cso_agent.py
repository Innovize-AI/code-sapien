from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model

from models.structured_output_cso import GlobalCSOBriefing
import json
import os
import logging

logger = logging.getLogger(__name__)

CSO_SYSTEM_PROMPT = """
You are the Chief Strategy Officer (Narrative Arbitrator). 
Your mission is to synthesize multiple streams of intelligence into a SINGLE prescriptive command. Use the `VERIFIED AGENTIC RAG BRIEFING` as your ground truth for product capabilities and evidence.

### STRATEGIC CLASSIFICATION:
You will receive a `lead_segment` (DIRECT_COMPETITOR, ADJACENT_PARTNER, POTENTIAL_CLIENT).
- **IF DIRECT_COMPETITOR**: DO NOT PITCH BASE FEATURES.
- **IF POTENTIAL_CLIENT**: Strategic Handshake focused on Peer Validation or Technical Curiosity. **BANNED**: No pitching or sales-talk in the first message.

CRITICAL ROLE:
1. ARBITRATOR: Resolve conflicts between agents.
2. STRATEGIST: Choose the optimal Messaging Framework (AIDA, PAS, BAB).
24. **COMMANDER**: Provide a one-sentence "Unified Command" and specify the exact product(s) identified in the `Proposed Solutions` or `Strategic RAG Briefing` to lead with.
25. **STRICT INDUSTRY NEUTRALITY**: You are BANNED from using industry-specific terminology or technical jargon (e.g., "MDR", "HIPAA") to describe products unless found verbatim in the `Strategic RAG Briefing`.
26. **ZERO TOLERANCE**: Never use generic buzzwords. Use ONLY the specific product names, service offerings, or strategic categories identified in your intelligence streams (RAG Briefing/Proposed Solutions).

### VERDICT TIERS (STRATEGIC THEMES):
You MUST adhere to these themes, but you MUST contextually customize the final `Command` and `verdict` for each lead:
1. **TIER 1 (Score 0-40): HARD DISQUALIFICATION.** 
   - **Theme**: Deprioritize. Explain the specific mismatch (e.g., "Company is in a Restricted Industry" or "Lead is a Direct Competitor").
   - **Command Guidelines**: Direct the rep to stop work on this lead.
2. **TIER 2 (Score 41-65): PASSIVE MONITOR.**
   - **Theme**: Caution. Identify the "Missing Signal" (e.g., "No decision-making power found" or "Low external activity").
   - **Command Guidelines**: Suggest low-intensity, non-sales interaction (e.g., "Request curiosity-based validation in comments").
3. **TIER 3 (Score 66-100): HIGH-PRIORITY STRIKE.**
   - **Theme**: High Viability. Use the **RAG Playbook Examples** immediately.
   - **Command Guidelines**: Prescribe a specific product hook identified in research.

ZERO TOLERANCE: Never issue a "Strike Now" theme if the score is below 65. Contextualize every command—never repeat the same sentence twice.

    ### DYNAMIC SEQUENCE PROTOCOL:
    When designing the `outreach_sequences`, you MUST use these exact `engagement_type` and `trigger` values:
    - **engagement_type**: `LI_WARM`, `LI_COMMENT`, `LI_INVITE`, `LI_DM`, `EMAIL_DIRECT`, `EMAIL_FOLLOWUP`, `BREAK_UP_EMAIL`.
    - **trigger**: `always` (for first steps or mandatory follow-ups), `if_no_reply` (for subsequent follow-ups).

    1. **RADAR WARMING (MANDATORY)**: 
    - **Step 1 (LI_COMMENT)** is ONLY used if recent posts exist. **Step 2 (LI_INVITE)** is ALWAYS required if LinkedIn is available.
    
    2. **DYNAMIC EMAIL PATHING**:
    - **UNAWARE / PROBLEM_AWARE (Start at Email Step 3 - EMAIL_DIRECT)**: Surface the friction. Use **INTEREST-BASED CTAs** (e.g., "Worth a look?").
    - **COST_AWARE (Start at Email Step 4 - EMAIL_FOLLOWUP)**: Focus on ROI/Value pivot. Use **INTEREST-BASED CTAs**.
    - **SOLUTION_AWARE / VENDOR_AWARE (Start at Email Step 5 - EMAIL_FOLLOWUP)**: Lead with Proof/Case Study. Use **TIME-BASED CTAs** (e.g., "Tuesday at 2?").
    3. **THE BREAK-UP (MANDATORY FINAL STEP)**:
    - Stage 6 MUST always be a `BREAK_UP_EMAIL`. Narrative angle: "Closing the loop" or "Permission to archive." If the `VERIFIED AGENTIC RAG BRIEFING` lists a 'Shareable Resource', you MUST explicitly instruct the Outreach Agent to offer it in the `internal_note`.

4. **LOOKALAKE SOCIAL PROOF**:
    - You MUST identify a `lookalike_peer` from the `VERIFIED AGENTIC RAG BRIEFING` (a competitor or company with a similar use case) to populate the `lookalike_peer` field.
    - **STRICT RULE**: If NO lookalike peer is found in the RAG context, you MUST set `lookalike_peer` to "N/A". NEVER invent a peer or use general industry knowledge.

### THE SPARSE CONTEXT PROTOCOL (STRICT):
If the `AVAILABLE SOLUTION POOL` contains a product but the intel (technical, narrative, collateral) is empty or sparse:
1. **NO EXTRAPOLATION**: You are BANNED from inventing industry-specific use cases (e.g., "MDR compliance" for MedTech) if they are not in the RAG context.
2. **CORE ONLY**: Stick to the base product definition provided.
3. **P.S. GROUNDING**: DO NOT suggest a "Proof Point" or "Peer" for a P.S. line in the `internal_note` unless it is explicitly in the RAG briefing. If you do, you will be BANNED.
4. **STRICT VERDICT GROUNDING**: Every `verdict`, `internal_note`, and `advanced_strategic_pivots` MUST be grounded in the `VERIFIED AGENTIC RAG BRIEFING`. Do not invent strategic angles, industry compliance needs, or "regulatory fits" that are not explicitly documented in your RAG stream.
5. **ZERO EVIDENCE HALLUCINATION**: Do not invent case studies, metrics, or "regulatory training" capabilities. If it's not in the RAG, it doesn't exist for the purpose of this outreach.

### STRATEGIC PIVOT PROTOCOL (CRITICAL):
If a Strategic Pivot product is selected (indicated by `Strategic Pivot Fit` being True or the selected product matching one of the `Pivot Product Names`), you MUST define a highly specific, concrete usecase or strategic vertical application in the `strategic_pivot_usecase` field.
- **Rules for specific usecase**:
  1. Base it strictly on the pain points and specific RAG playbooks or RAG context provided for that product (e.g., if the pivot product is Glial and the lead is in Logistics, the usecase should be "Automated lead discovery and LinkedIn active listening for 3PL sales leaders").
  2. The usecase must represent a highly tactical, real-world application of the product's core capabilities that addresses the lead's specific business context.
  3. If no strategic pivot is selected or appropriate, set `strategic_pivot_usecase` to "N/A" or "None".

### DRAFTS:
You must NEVER write actual outreach drafts. Provide only the strategy, angle, and signals.
"""

def narrative_arbitrator_node(state: AgentState):
    """
    The final strategic layer. Consolidation of all agent findings + Knowledge Base RAG.
    """
    # 1. Gather context from previous nodes
    lead_score = state.get("lead_score_analysis", {})
    pain_points = state.get("target_pain_points", {})
    persona = state.get("user_profile_analysis", {}).get("engagement_persona", "Unknown")
    
    # Solution Pool Context (New) - Handle potential JSON string serialization
    solution_pool = state.get("research_solution_pool", [])
    if isinstance(solution_pool, str):
        try:
            solution_pool = json.loads(solution_pool)
        except:
            logger.warning("CSO Agent: Could not parse research_solution_pool string as JSON")
            solution_pool = []
    
    # Pivot Context
    is_strategic_pivot_fit = state.get("is_strategic_pivot_fit", False)
    pivot_product_names = state.get("pivot_product_names", [])
    
    # 2. Build the Strategic Synthesis Prompt
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    
    # Calculate post count for conditional logic
    raw_posts = state.get("user_profile_details", {}).get("recent_posts", [])
    from agents.linkedin_agent import is_recent_post
    recent_posts = [p for p in raw_posts if is_recent_post(p)]
    recent_posts_count = len(recent_posts)

    analysis_str = json.dumps(lead_score)
    penalty = lead_score.get("negative_penalty", 0)
    penalty_reason = lead_score.get("penalty_reason", "")
    
    alert_section = ""
    if penalty > 0:
        alert_section = f"""
    !!! CRITICAL NEGATIVE SIGNAL DETECTED !!!
    - PENALTY APPLIED: {penalty} points deducted.
    - REASON: {penalty_reason}
    - ACTION REQUIRED: Consider this account "High Risk".
    """

    # Format Solution Pool for the CSO
    pool_str = ""
    for idx, p in enumerate(solution_pool):
        # Defensive check: Ensure 'p' is a dictionary
        if not isinstance(p, dict):
            logger.warning(f"CSO Agent: Skipping malformed solution entry at index {idx} (Expected dict, got {type(p)})")
            continue
            
        pool_str += f"""
--- SOLUTION OPTION {idx+1}: {p.get('product_name', 'Unknown Product')} ---
- TECHNICAL INTEL: {p.get('technical_intel', 'N/A')}
- NARRATIVE/MESSAGING: {p.get('narrative_intel', 'N/A')}
- COLLATERAL/PROOF: {p.get('collateral_intel', 'N/A')}
- OBJECTIONS/FRICTION: {p.get('objections', 'N/A')}
- ATTACHED ASSETS: {", ".join(p.get('attached_playbooks', []) + p.get('attached_case_studies', []))}
"""

    synthesis_input = f"""
    LEAD INTELLIGENCE:
    - Person: {persona}
    - Lead Segment: {lead_segment}
    - Recent LinkedIn Posts Found: {recent_posts_count}
    - Lead Score Analysis: {analysis_str}
    {alert_section}
    - Strategic Pivot Fit: {is_strategic_pivot_fit}
    - Pivot Product Names: {pivot_product_names}
    - Identified Pain Points: {json.dumps(pain_points)}
    - STRATEGIC RECOMMENDATION (CRM & JOURNEY): {state.get('strategic_recommendation')}
    - INTENT ANALYSIS (EMAIL/SENTIMENT): {state.get('intent_analysis')}
    - SYNTHESIZED STRATEGIC SOLUTIONS: {json.dumps(state.get('strategic_solutions', []))}

    AVAILABLE SOLUTION POOL (Surgically Researched):
    {pool_str if pool_str else "No qualified solutions found."}

    YOUR MISSION (Surgical Strategy & Executive Selection):
    1. **INTENT & JOURNEY SYNC**: Align with the `STRATEGIC RECOMMENDATION`.
    2. **PRODUCT SELECTION (CRITICAL)**: 
       - Review the `AVAILABLE SOLUTION POOL` and `SYNTHESIZED STRATEGIC SOLUTIONS`. 
       - Select the **SINGLE BEST** product or service that solves the `Identified Pain Points`.
       - If `Strategic Pivot Fit` is True, you MUST prioritize the pivot product unless there is a catastrophic mismatch.
       - Provide the `selected_product_name` and a logical `selected_product_justification`.
       - **STRATEGIC PIVOT USECASE**: If a strategic pivot product is selected, define the exact concrete context-targeted application in the `strategic_pivot_usecase` field.
       - **GROUNDING CHECK**: Your selection MUST exist in the provided solutions. DO NOT invent a product or service.
    3. **DYNAMIC SOCIAL STEPS**: 
       - **IF Recent LinkedIn Posts > 0**: Start with Stage 1 (LI_COMMENT).
       - **IF Recent LinkedIn Posts == 0**: BANNED from using LI_COMMENT. Skip to Stage 2 (LI_INVITE).
    4. **SEQUENCE ARCHITECTURE (MANDATORY)**:
       - Stage 1: LI_COMMENT (trigger: always) - ONLY if posts exist.
       - Stage 2: LI_INVITE (trigger: always) - MANDATORY.
       - Stage 3: EMAIL_DIRECT (trigger: if_no_reply)
       - Stage 4: EMAIL_FOLLOWUP (trigger: if_no_reply)
       - Stage 5: EMAIL_FOLLOWUP (trigger: if_no_reply)
       - Stage 6: BREAK_UP_EMAIL (trigger: if_no_reply)
    5. **MULTI-VARIANT SELECTION**: Generate EXACTLY TWO distinct `OutreachBlueprint` variants.
    """

    messages = [
        SystemMessage(content=CSO_SYSTEM_PROMPT),
        HumanMessage(content=synthesis_input)
    ]

    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0).with_structured_output(GlobalCSOBriefing)
        response = model.invoke(messages)
        
        if not response:
            return {"cso_strategic_briefing": {}}
            
        # Find the selected product's intel from the pool to pass downstream
        winning_intel = ""
        selected_name = response.selected_product_name
        for p in solution_pool:
            # Defensive check for second loop
            if not isinstance(p, dict):
                continue
                
            if p.get('product_name', '').lower() in selected_name.lower() or selected_name.lower() in p.get('product_name', '').lower():
                sources = p.get('attached_playbooks', []) + p.get('attached_case_studies', [])
                winning_intel = f"PRODUCT: {p['product_name']}\n\nTECHNICAL:\n{p['technical_intel']}\n\nNARRATIVE/MESSAGING:\n{p['narrative_intel']}\n\nCOLLATERAL/PROOF:\n{p['collateral_intel']}\n\nOBJECTIONS:\n{p['objections']}\n\nSOURCES/PLAYBOOKS:\n{', '.join(sources) if sources else 'N/A'}"
                break
        
        # If no exact match, use a fallback of the first one if only one exists
        if not winning_intel and solution_pool:
            winning_intel = f"SELECTED PRODUCT: {selected_name}\n(Context mapping fallback applied)"

        return {
            "cso_strategic_briefing": response.model_dump(),
            "strategic_rag_briefing": winning_intel # Pass the WINNING intel to the outreach agents
        }
    except Exception as e:
        logger.error(f"Error in narrative_arbitrator_node: {e}", exc_info=True)
        return {"cso_strategic_briefing": {}}
