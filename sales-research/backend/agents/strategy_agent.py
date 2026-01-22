from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.openai_models import get_open_ai
from prompts.sales_prompts import (
    VIABILITY_ASSESSMENT_PROMPT, 
    PAIN_POINT_DISCOVERY_PROMPT, 
    STRATEGIC_SOLUTION_PROMPT, 
    OUTREACH_DESIGN_PROMPT
)
import json


def viability_node(state: AgentState):
    """Evaluates the lead against the Ideal Customer Profile (ICP)."""
    user_analysis = state.get("user_profile_analysis", "")
    website_analysis = state.get("website_analysis", "")
    company_stats = state.get("company_stats", {})
    ideal_profile = state.get("ideal_profile")
    
    prompt = VIABILITY_ASSESSMENT_PROMPT.format(
        icp=ideal_profile.json() if hasattr(ideal_profile, 'json') else str(ideal_profile),
        user_analysis=user_analysis,
        website_analysis=website_analysis,
        company_stats=json.dumps(company_stats)
    )

    
    messages = [
        SystemMessage(content="You are a strategic sales consultant."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"viability_analysis": response.content}

def pain_point_node(state: AgentState):
    """Identifies specific, actionable pain points from the lead's profile and company footprint."""
    user_analysis = state.get("user_profile_analysis", "")
    website_analysis = state.get("website_analysis", "")
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
        SystemMessage(content="You are an expert business analyst."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"target_pain_points": response.content}

def solution_node(state: AgentState):
    """Maps identified pain points to Innovize AI's specific offerings."""
    pain_points = state.get("target_pain_points", "")
    company_context = state.get("company_context", "")
    
    prompt = STRATEGIC_SOLUTION_PROMPT.format(
        pain_points=pain_points,
        company_context=company_context
    )

    
    messages = [
        SystemMessage(content="You are a technical solutions architect."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"strategic_solutions": response.content}

def outreach_node(state: AgentState):
    """Crafts the personalized "hook" and outbound message."""
    user_analysis = state.get("user_profile_analysis", "")
    solutions = state.get("strategic_solutions", "")
    engagements = state.get("post_engagements", [])
    
    prompt = OUTREACH_DESIGN_PROMPT.format(
        user_analysis=user_analysis,
        engagements=json.dumps(engagements),
        solutions=solutions
    )

    
    messages = [
        SystemMessage(content="You are a high-performance sales copywriter."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"personalized_outreach": response.content}
