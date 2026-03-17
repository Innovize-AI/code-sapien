from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from services.knowledge_service import KnowledgeService
from models.structured_output_cso import GlobalCSOBriefing
import json
import os

# Initialize KnowledgeService
knowledge_service = KnowledgeService(index_name="glial-index")

CSO_SYSTEM_PROMPT = """
You are the Chief Strategy Officer (Narrative Arbitrator) at {selling_company_name}. 
Your mission is to synthesize multiple streams of intelligence into a SINGLE prescriptive command.

### STRATEGIC CLASSIFICATION:
You will receive a `lead_segment` (DIRECT_COMPETITOR, ADJACENT_PARTNER, POTENTIAL_CLIENT).
- **IF DIRECT_COMPETITOR**: DO NOT PITCH BASE FEATURES.
- **IF POTENTIAL_CLIENT**: Standard direct pitch for ROI using our product suite.

CRITICAL ROLE:
1. ARBITRATOR: Resolve conflicts between agents.
2. STRATEGIST: Choose the optimal Messaging Framework (AIDA, PAS, BAB).
3. COMMANDER: Provide a one-sentence "Unified Command" and specify the exact product from our suite ({selling_products_list}) to lead with. FOR COMPETITORS: Always lead with **Glial** (Intelligence Infrastructure) or **Strategic Consulting**.

ZERO TOLERANCE: Never use generic product terms. Use ONLY the validated product names from our portfolio.

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
    
    # 2. Build the Strategic Synthesis Prompt
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    selling_profile = state.get("selling_company_profile")
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    selling_products_list = ", ".join([p.name for p in selling_profile.products]) if selling_profile else "Glial, IDP, Agentic KB"
    
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
    6. COMMAND: Issue a one-sentence "Unified Command" that is prescriptive. If a "Poor Fit" or "High Risk", command to "Monitor" or "Deprioritize". If "Good Fit", command to "Strike".
    7. JUSTIFY PRODUCT: Explicitly explain why you chose a specific Product (e.g., Glial). If "Poor Fit", explain why we should NOT pitch.
    8. **SCORE CITATION**: In your `strategic_reasoning`, you MUST explicitly cite the 'Total Lead Score' and the key drivers (e.g., 'High Demographic Fit', 'Low Engagement') that led to your verdict.
    9. EXTRACT PROOFS: List the underlying specific insights used in `strategic_proof_points`.
    10. GUIDANCE: Provide the `refined_linkedin_message` and `refined_email_body` as STRATEGIC BLUEPRINTS. Use the **Strategic Handshake** (LinkedIn) and **Logical Gap Body** (Email) rules.
    11. **WEIGHTED TONE**: Ensure the final output is professional, calm, and focused on the prospect's needs. Use a 7th-grade reading level.
    """

    messages = [
        SystemMessage(content=CSO_SYSTEM_PROMPT.format(
            selling_company_name=selling_company_name,
            selling_products_list=selling_products_list
        )),
        HumanMessage(content=synthesis_input)
    ]

    try:
        # Using GPT-4o for high-fidelity strategic synthesis
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0).with_structured_output(GlobalCSOBriefing)
        response = model.invoke(messages)
        
        return {"cso_strategic_briefing": response.model_dump() if response else {}}
    except Exception as e:
        print(f"Error in narrative_arbitrator_node: {e}")
        return {"cso_strategic_briefing": {}}
