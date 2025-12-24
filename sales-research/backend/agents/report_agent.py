from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import REPORT_GENERATOR_PROMPT
from models.openai_models import get_open_ai

def sales_research_report_generator(state: AgentState):
    user_profile_analysis = state['user_profile_analysis']
    website_analysis = state["website_analysis"]
    company_context = state["company_context"]
    lead_score_analysis = state["lead_score_analysis"]
    
    content = f"{user_profile_analysis} {website_analysis} {lead_score_analysis}"
    
    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT.format(content=content)),
        HumanMessage(content=f"company context : {company_context}")
    ]

    llm = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = llm.invoke(messages)

    return {"sales_research_report": response.content}
