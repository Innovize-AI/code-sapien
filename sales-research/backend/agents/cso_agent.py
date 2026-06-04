from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model

from models.structured_output_cso import GlobalCSOBriefing
import json
import os
import logging

logger = logging.getLogger(__name__)

CSO_BASE_SYSTEM_PROMPT = """
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
   - **Hiring Signals**: If active job postings or hiring data are present and match our solution set, prioritize generating a Tier 3 "Strike Now" verdict that explicitly leverages the specific open role, hiring managers, and active operational hiring pain as a timely outreach trigger.

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

### ACTIVE HIRING TARGETING PROTOCOL (NON-NEGOTIABLE):
If `Active Hiring Data / Job Postings` are present and contain active roles or descriptions:
1. **Systematic Role-to-Product Mapping**: You MUST analyze the job roles/titles being hired for and their associated duties from the hiring data. Match these active roles and manual tasks directly to the most appropriate products or capabilities documented in the `AVAILABLE SOLUTION POOL` and verified playbooks.
2. **Dynamic Custom Workflow Generation**: If the open role represents a manual, operational bottleneck that does not perfectly fit any standard product in the pool, you MUST dynamically design and name a specific, professional, and context-tailored automated workflow targeting that exact role (e.g. naming it "Automated [Role Name] Workflow" or "AI [Department/Task] Pipeline"). Never use a generic fallback.
3. **Outreach Alignment**: Instruct the Outreach Agent in the `internal_note` to pitch this selected product or dynamically designed workflow as a direct solution to their hiring pain—allowing them to automate the repetitive aspects of that open position, scale operations, and bypass the recruitment/onboarding bottleneck.

### STRATEGIC PIVOT PROTOCOL (CRITICAL):
If a Strategic Pivot product is selected (indicated by `Strategic Pivot Fit` being True or the selected product matching one of the `Pivot Product Names`), you MUST define a highly specific, concrete usecase or strategic vertical application in the `strategic_pivot_usecase` field.
- **Rules for specific usecase**:
  1. Base it strictly on the pain points and specific RAG playbooks or RAG context provided for that product (e.g., if the pivot product is Glial and the lead is in Logistics, the usecase should be "Automated lead discovery and LinkedIn active listening for 3PL sales leaders").
  2. The usecase must represent a highly tactical, real-world application of the product's actual capabilities (e.g., "Automating accounts payable invoice ingestion into NetSuite", "Automated RFQ parsing to draft proposal PDFs", or "Consolidating data pipelines to eliminate manual weekly spreadsheet reporting") that addresses the lead's specific business context.
  3. **STRICT PRODUCT GROUNDING**: You are ABSOLUTELY BANNED from inventing fake services, custom diagnostic frameworks, auditing methodologies, or specialized assessments (e.g., "technical diagnostic mapping that audits TMS process data") that the selling company does not actually offer. The usecase MUST map directly to actual features or offerings documented in the selected product's playbook/RAG context.
  4. If no strategic pivot is selected or appropriate, set `strategic_pivot_usecase` to "N/A" or "None".

### COLLABORATIVE DISCOVERY & SIMPLICITY PROTOCOLS (MANDATORY):
1. **ELIMINATE ACADEMIC & HIGH-LEVEL BUZZWORDS**:
   - You are ABSOLUTELY BANNED from suggesting hyper-intellectual, academic, or high-level strategic buzzwords (e.g., "closing the perception gap through custom digital infrastructure frameworks", "resolving systemic alignment through integrated technical paradigms").
   - Every `internal_note`, `strategic_pivot_usecase`, and prescribed strategy must focus on **grounded, everyday operations and back-office manual workflows** (e.g., "reconciling signed delivery receipts," "converting raw logs/CSVs into client summaries," "triaging shared email inboxes").
2. **THE COLLABORATIVE DISCOVERY PLAY**:
   - Instead of instructing the Outreach Agent to pitch a single highly speculative, locked-in custom technical solution (which might not exist or might miss their exact tech stack), you MUST prescribe a **Collaborative Discovery** strategy in the `internal_note`.
   - The strategy must guide the Outreach Agent to present **2 or 3 of our broader, vetted template capabilities** (e.g., Automated Reporting, Back-Office Document Parsing, or Inbox Triage) as clear, practical options, and offer a short collaborative call to map out their specific manual bottlenecks together.

### DRAFTS:
You must NEVER write actual outreach drafts. Provide only the strategy, angle, and signals.
"""

INNOVIZEAI_PROMPT_SECTION = """
### STRICT PRODUCT SELECTION BANS & PROTOCOLS (NON-NEGOTIABLE)- Specific for InnovizeAI:
1. **NEVER SAY "AI TRANSFORMATION" OR "AI TRANSFORMATION SERVICES"**:
   - You are ABSOLUTELY FORBIDDEN from outputting "AI Transformation" or "AI Transformation Services" as the `selected_product_name`.
2. **USE SPECIFIC PLAYBOOK USE CASES**:
   - If the qualified product fits the "AI Transformation Services" offering, you MUST match the prospect's specific pain points and signals against the following 5 specialized use cases from the internal playbook:
     * `Invoice Processing Automation` (for Accounts Payable / finance pains)
     * `RFQ and Quote Automation` (for bidding, estimating, sales proposal bottleneck pains)
     * `Inbox Automation` (for customer service, shared inbox, high email volume triage pains)
     * `Document Processing Automation` (for back-office transcription, manual data entry, PDF/BOL parsing pains)
     * `Reporting Automation` (for manual weekly spreadsheet preparation, reporting backlog, Excel consolidation pains)
   - Select the single most relevant usecase as the `selected_product_name`.
3. **FALLBACK TO CUSTOM WORKFLOW CREATION**:
   - If the prospect's signal indicates a clear operational pain point that does NOT map to any of the above 5 use cases, you MUST dynamically build and design a specific new workflow name tailored directly to their pain (e.g., "Automated Customer Onboarding Pipeline" or "Forensic Claims Processing Workflow") and use that as the `selected_product_name`.
   - Never fallback to a generic product name. Every selected product must sound tailored, real, and professional.
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
            
    # Normalize dict-like solution_pool or list of strings
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
            
    # Active Hiring/Job posting data (New)
    hiring_data = state.get("hiring_data", [])
    if isinstance(hiring_data, str):
        try:
            hiring_data = json.loads(hiring_data)
        except:
            logger.warning("CSO Agent: Could not parse hiring_data string as JSON")
            hiring_data = []
    
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
    - Active Hiring Data / Job Postings: {json.dumps(hiring_data)}
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
 
    selling_profile = state.get("selling_company_profile")
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    is_innovize = (selling_company_name.lower() == "innovize ai") or (os.getenv("IS_INNOVIZEAI", "false").lower() == "true")
    
    system_prompt = CSO_BASE_SYSTEM_PROMPT
    if is_innovize:
        system_prompt += "\n\n" + INNOVIZEAI_PROMPT_SECTION
        
    messages = [
        SystemMessage(content=system_prompt),
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
        
        # Check direct matches first
        for p in solution_pool:
            if not isinstance(p, dict):
                continue
            p_name = p.get('product_name', '')
            if p_name.lower() in selected_name.lower() or selected_name.lower() in p_name.lower():
                sources = p.get('attached_playbooks', []) + p.get('attached_case_studies', [])
                winning_intel = f"PRODUCT: {p_name}\n\nTECHNICAL:\n{p.get('technical_intel', 'N/A')}\n\nNARRATIVE/MESSAGING:\n{p.get('narrative_intel', 'N/A')}\n\nCOLLATERAL/PROOF:\n{p.get('collateral_intel', 'N/A')}\n\nOBJECTIONS:\n{p.get('objections', 'N/A')}\n\nSOURCES/PLAYBOOKS:\n{', '.join(sources) if sources else 'N/A'}"
                break
                
        # If no direct match (due to specific usecase/custom workflow selection), map to AI Transformation Services
        if not winning_intel:
            for p in solution_pool:
                if not isinstance(p, dict):
                    continue
                p_name = p.get('product_name', '')
                if "ai transformation" in p_name.lower() or "transformation services" in p_name.lower():
                    sources = p.get('attached_playbooks', []) + p.get('attached_case_studies', [])
                    winning_intel = f"PRODUCT: {selected_name} (tailored from {p_name})\n\nTECHNICAL:\n{p.get('technical_intel', 'N/A')}\n\nNARRATIVE/MESSAGING:\n{p.get('narrative_intel', 'N/A')}\n\nCOLLATERAL/PROOF:\n{p.get('collateral_intel', 'N/A')}\n\nOBJECTIONS:\n{p.get('objections', 'N/A')}\n\nSOURCES/PLAYBOOKS:\n{', '.join(sources) if sources else 'N/A'}"
                    break
        
        # Fallback to the first available solution if still not mapped
        if not winning_intel and solution_pool:
            p = solution_pool[0]
            sources = p.get('attached_playbooks', []) + p.get('attached_case_studies', [])
            winning_intel = f"PRODUCT: {selected_name} (context fallback)\n\nTECHNICAL:\n{p.get('technical_intel', 'N/A')}\n\nNARRATIVE/MESSAGING:\n{p.get('narrative_intel', 'N/A')}\n\nCOLLATERAL/PROOF:\n{p.get('collateral_intel', 'N/A')}\n\nOBJECTIONS:\n{p.get('objections', 'N/A')}\n\nSOURCES/PLAYBOOKS:\n{', '.join(sources) if sources else 'N/A'}"

        return {
            "cso_strategic_briefing": response.model_dump(),
            "strategic_rag_briefing": winning_intel # Pass the WINNING intel to the outreach agents
        }
    except Exception as e:
        logger.error(f"Error in narrative_arbitrator_node: {e}", exc_info=True)
        return {"cso_strategic_briefing": {}}
