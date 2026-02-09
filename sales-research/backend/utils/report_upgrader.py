from langchain_core.messages import SystemMessage, HumanMessage
from models.openai_models import get_open_ai
from models.structured_output import ViabilityAssessment, PainPoints, StrategicSolutions, OutreachStrategy
import json

UPGRADE_PROMPT = """
You are a Research Data Analyst. Your task is to take a legacy Research Report (unstructured text) and re-distribute its content into the new modular analysis categories.

LEGACY REPORT TEXT:
{legacy_text}

TRANSFORMATION RULES:
1. Extract content for each specific category below.
2. If the legacy text doesn't contain specific info for a category, use your professional judgment to infer it based on the available context, but keep it grounded in the original report.
3. Ensure the formatting remains professional.
"""

def upgrade_legacy_content(legacy_text: str):
    """Uses LLM to split legacy text into modular fields."""
    if not legacy_text:
        return {}

    model = get_open_ai(model="gpt-4o-mini")
    
    # 1. Extract Viability
    v_model = model.with_structured_output(ViabilityAssessment)
    v_res = v_model.invoke([
        SystemMessage(content="Extract the viability assessment from the legacy report."),
        HumanMessage(content=legacy_text)
    ])
    
    # 2. Extract Pain Points
    p_model = model.with_structured_output(PainPoints)
    p_res = p_model.invoke([
        SystemMessage(content="Extract specific pain points identified in the legacy report."),
        HumanMessage(content=legacy_text)
    ])
    
    # 3. Extract Solutions
    s_model = model.with_structured_output(StrategicSolutions)
    s_res = s_model.invoke([
        SystemMessage(content="Extract the proposed solutions from the legacy report."),
        HumanMessage(content=legacy_text)
    ])
    
    # 4. Extract Outreach
    o_model = model.with_structured_output(OutreachStrategy)
    o_res = o_model.invoke([
        SystemMessage(content="Extract the outreach hooks and messages from the legacy report."),
        HumanMessage(content=legacy_text)
    ])

    # Convert to Markdown (similar to agents)
    viability_md = f"### Strategic Viability: {v_res.verdict}\n**Score: {v_res.score}/10**\n\n#### Demographic Fit\n{v_res.demographic_fit}\n\n#### Authority\n{v_res.authority}\n\n#### Strategic Alignment\n{v_res.strategic_alignment}"
    
    pain_md = "### Identified Pain Points\n\n"
    for pt in p_res.points:
        pain_md += f"#### {pt.title}\n- **Challenge:** {pt.description}\n- **Impact:** {pt.impact}\n\n"
        
    solutions_md = "### Strategic Solutions\n\n"
    for sol in s_res.solutions:
        solutions_md += f"#### {sol.title}\n- **Solution:** {sol.description}\n- **Expected ROI:** {sol.expected_roi}\n\n"
        
    outreach_md = f"### Personalized Outreach Design\n\n#### 🪝 The Hook\n{o_res.hook}\n\n#### 💬 LinkedIn Message\n{o_res.linkedin_message}\n\n#### 📧 Email Outreach\n**Subject:** {o_res.email_subject}\n\n{o_res.email_body}"

    return {
        "viability_analysis": viability_md,
        "target_pain_points": pain_md,
        "strategic_solutions": solutions_md,
        "personalized_outreach": outreach_md
    }
