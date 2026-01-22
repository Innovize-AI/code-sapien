from langchain_core.messages import SystemMessage, HumanMessage
import json
from workflow.state import AgentState
from prompts.sales_prompts import LEAD_SCORER_SYSTEM_PROMPT, LEAD_DATA_EXTRACTOR_PROMPT
from models.openai_models import get_open_ai

def lead_data_extractor(state: AgentState):
    user_profile_analysis = state['user_profile_analysis']
    website_analysis = state["website_analysis"]
    input_lead_data = state["input_lead_data"]
    company_stats = state.get("company_stats", {})

    lead_data_json = input_lead_data.json()
    lead_data = f"USER ANALYSIS: {user_profile_analysis}\nWEBSITE ANALYSIS: {website_analysis}\nCOMPANY STATS: {json.dumps(company_stats)}\nINPUT DATA: {lead_data_json}"


    messages = [
        SystemMessage(content=LEAD_DATA_EXTRACTOR_PROMPT),
        HumanMessage(content=lead_data)
    ]

    llm = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = llm.invoke(messages)

    return {"lead_extracted_data": response.content}

def lead_scorer(state: AgentState):
    lead_extracted_data = state["lead_extracted_data"]
    ideal_profile = state["ideal_profile"]
    ideal_profile_json = ideal_profile.json()

    messages = [
        SystemMessage(content=LEAD_SCORER_SYSTEM_PROMPT.format(content=ideal_profile_json)),
        HumanMessage(content=lead_extracted_data)
    ]

    llm = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = llm.invoke(messages)

    return {"lead_score_analysis": response.content}
