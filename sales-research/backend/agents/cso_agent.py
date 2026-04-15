from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from services.knowledge_service import KnowledgeService
from models.structured_output_cso import GlobalCSOBriefing
import json
import os
import logging

logger = logging.getLogger(__name__)

# Initialize KnowledgeService
knowledge_service = KnowledgeService(index_name="glial-index")

CSO_SYSTEM_PROMPT = """
You are the Chief Strategy Officer (Narrative Arbitrator). 
Your mission is to synthesize multiple streams of intelligence into a SINGLE prescriptive command. Use the `VERIFIED AGENTIC RAG BRIEFING` as your ground truth for product capabilities and evidence.

### STRATEGIC CLASSIFICATION:
You will receive a `lead_segment` (DIRECT_COMPETITOR, ADJACENT_PARTNER, POTENTIAL_CLIENT).
- **IF DIRECT_COMPETITOR**: DO NOT PITCH BASE FEATURES.
- **IF POTENTIAL_CLIENT**: Standard direct pitch for ROI using the proposed solutions.

CRITICAL ROLE:
1. ARBITRATOR: Resolve conflicts between agents.
2. STRATEGIST: Choose the optimal Messaging Framework (AIDA, PAS, BAB).
3. COMMANDER: Provide a one-sentence "Unified Command" and specify the exact product(s) identified in the `Proposed Solutions` or `Strategic RAG Briefing` to lead with. The command MUST be hyper-specific to the solutions found in your intelligence streams.

ZERO TOLERANCE: Never use generic product terms. Use ONLY the specific product names identified in your intelligence streams.

### THE STRATEGIC HANDSHAKE (LINKEDIN RULE):
- **refined_linkedin_message** MUST be strictly under 250 characters.
- It must be a **Handshake**, not a Pitch. No "helping to scale," no discovery questions, no sales jargon.
- Use a **"Technical Critique"** or **"Peer Validation"** angle. Disarm the prospect by acknowledging how their current manual work might be holding them back. 
- **LANGUAGE**: Use a 7th-grade reading level. No complex metaphors. Focus on the prospect's needs.
"""

def narrative_arbitrator_node(state: AgentState):
    """
    The final strategic layer. Consolidation of all agent findings + Knowledge Base RAG.
    """
    # 1. Gather context from previous nodes
    lead_score = state.get("lead_score_analysis", {})
    pain_points = state.get("target_pain_points", {})
    solutions = state.get("strategic_solutions", {})
    persona = state.get("user_profile_analysis", {}).get("engagement_persona", "Unknown")
    rag_briefing = state.get("strategic_rag_briefing", "No RAG briefing available.")
    
    # Pivot Context (New)
    is_strategic_pivot_fit = state.get("is_strategic_pivot_fit", False)
    pivot_product_name = state.get("pivot_product_name", "N/A")
    
    # 2. Build the Strategic Synthesis Prompt
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    
    analysis_str = json.dumps(lead_score)
    penalty = lead_score.get("negative_penalty", 0)
    penalty_reason = lead_score.get("penalty_reason", "")
    
    alert_section = ""
    if penalty > 0:
        alert_section = f"""
    !!! CRITICAL NEGATIVE SIGNAL DETECTED !!!
    - PENALTY APPLIED: {penalty} points deducted.
    - REASON: {penalty_reason}
    - ACTION REQUIRED: You MUST consider this a "High Risk" or "Do Not Follow-up" scenario unless there is overwhelming evidence otherwise.
    """

    synthesis_input = f"""
    LEAD INTELLIGENCE:
    - Persona: {persona}
    - Lead Segment: {lead_segment}
    - Lead Score Analysis: {analysis_str}
    {alert_section}
    - Strategic Pivot Fit: {is_strategic_pivot_fit}
    - Pivot Product Name: {pivot_product_name}
    - Pain Points: {json.dumps(pain_points)}
    - Proposed Solutions: {json.dumps(solutions)}

    VERIFIED AGENTIC RAG BRIEFING:
    {rag_briefing}

    YOUR MISSION (Surgical Strategy & Evidence Selection):
    1. **VIABILITY CHECK (CRITICAL)**: Analyze the `Lead Score Analysis`. If the score is low (<50) or the `fit_assessment` from other agents suggests a "Poor Fit", your verdict MUST account for this. Do NOT blindly issue a "Green Light" if the data says "STOP".
    2. **IDENTIFY LOGICAL GAPS**: For a "Good Fit", identify the **"Logical Gap"** or **"Silent Friction"** (e.g., lost productivity due to manual research) between their current activities and their goals. 
    3. STRATEGIZE: Based on the Lead Intelligence and Strategic Playbooks, determine the winning Narrative of Opportunity (OR Disqualification Reason).
    4. SELECT FRAMEWORK: Choose the optimal Messaging Framework (AIDA, PAS, BAB) from the playbooks. Explicitly explain WHY this framework fits the lead's persona (e.g., 'Skeptical technical buyers need PAS to validate pain first').
    5. IDENTIFY PROOF: From the "STRATEGIC PLAYBOOKS", identify 1-2 powerful "Proof Points".
    6. COMMAND: Issue a one-sentence "Unified Command" that is prescriptive and HYPER-SPECIFIC. If a "Poor Fit" or "High Risk", command to "Monitor" or "Deprioritize". If "Good Fit", command to "Strike".
    7. PITCH JUSTIFICATION (BRANCHING LOGIC):
        - **IF Strategic Pivot Fit is TRUE**: Provide a detailed justification for the `{pivot_product_name}`. Use the RAG briefing to explain how its specific features address the lead's unique friction.
        - **IF Strategic Pivot Fit is FALSE**: Shift to **"Solution Based Pitching"**. Focus your justification on how the broader `Proposed Solutions` and AI transformation capabilities map directly to the organizational `Pain Points`.
    8. **SCORE CITATION**: In your `strategic_reasoning`, you MUST explicitly cite the 'Total Lead Score' and the key drivers (e.g., 'High Demographic Fit', 'Low Engagement') that led to your verdict.
    9. EXTRACT PROOFS: List the underlying specific insights used in `strategic_proof_points`.
    10. GUIDANCE: Provide the `refined_linkedin_message` and `refined_email_body` as STRATEGIC BLUEPRINTS. Use the **Strategic Handshake** (LinkedIn) and **Logical Gap Body** (Email) rules.
    11. **WEIGHTED TONE**: Ensure the final output is professional, calm, and focused on the prospect's needs. Use a 7th-grade reading level.
    """

    messages = [
        SystemMessage(content=CSO_SYSTEM_PROMPT),
        HumanMessage(content=synthesis_input)
    ]

    try:
        # Using GPT-4o for high-fidelity strategic synthesis
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0).with_structured_output(GlobalCSOBriefing)
        response = model.invoke(messages)
        
        return {"cso_strategic_briefing": response.model_dump() if response else {}}
    except Exception as e:
        logger.error(f"Error in narrative_arbitrator_node: {e}")
        return {"cso_strategic_briefing": {}}
