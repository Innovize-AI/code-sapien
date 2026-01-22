from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
import json

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
    
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    company_industries = state.get("company_industries", [])
    company_stats = state.get("company_stats", {})
    
    input_content = f"""
    1. COMPANY INTELLIGENCE:
    - Name: {company_name}
    - Description: {company_description}
    - Industries: {", ".join(company_industries) if isinstance(company_industries, list) else company_industries}
    - Stats: {json.dumps(company_stats) if company_stats else "N/A"}

    2. PERSONA ANALYSIS SUMMARY:
    {user_profile_analysis}
    
    3. WEBSITE & COMPANY POSITIONING:
    {website_analysis}
    
    4. QUALIFICATION DATA & INTENT:
    {lead_score_analysis}
    
    5. STRATEGIC EVALUATIONS:
    - ICP Viability Analysis: {viability}
    - Discovered Pain Points: {pain_points}
    - Proposed Strategic Solutions: {solutions}
    - Outreach Strategy Design: {outreach}
    """
    
    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT.format(
            content=input_content,
        )),
        HumanMessage(content=f"Synthesize the research for this prospect. Company context: {company_context}")
    ]

    llm = get_open_ai(model="gpt-4o", temperature=0.7) # GPT-4o for strategic synthesis
    response = llm.invoke(messages)

    return {"sales_research_report": response.content}


