from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import REPORT_GENERATOR_PROMPT
from models.openai_models import get_open_ai

def sales_research_report_generator(state: AgentState):
    user_profile_analysis = state.get('user_profile_analysis', '')
    website_analysis = state.get("website_analysis", "")
    company_context = state.get("company_context", "")
    lead_score_analysis = state.get("lead_score_analysis", "")
    
    # New Modular Content
    viability = state.get("viability_analysis", "")
    pain_points = state.get("target_pain_points", "")
    solutions = state.get("strategic_solutions", "")
    outreach = state.get("personalized_outreach", "")
    
    input_content = f"""
    PERSONA ANALYSIS:
    {user_profile_analysis}
    
    WEBSITE ANALYSIS:
    {website_analysis}
    
    LEAD SCORE & INTENT:
    {lead_score_analysis}
    
    STRATEGIC MODULARS:
    - Viability: {viability}
    - Identified Pain Points: {pain_points}
    - Proposed Solutions: {solutions}
    - Outreach Strategy: {outreach}
    """
    
    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT.format(content=input_content)),
        HumanMessage(content=f"Company context for Innovize AI: {company_context}")
    ]

    llm = get_open_ai(model="gpt-4o", temperature=1) # Use gpt-4o for final synthesis
    response = llm.invoke(messages)

    return {"sales_research_report": response.content}

