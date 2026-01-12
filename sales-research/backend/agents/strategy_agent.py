from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.openai_models import get_open_ai
import json

def viability_node(state: AgentState):
    """Evaluates the lead against the Ideal Customer Profile (ICP)."""
    user_analysis = state.get("user_profile_analysis", "")
    website_analysis = state.get("website_analysis", "")
    ideal_profile = state.get("ideal_profile")
    
    prompt = f"""
    Evaluate the strategic viability of this lead based on the following Ideal Customer Profile (ICP):
    {ideal_profile.json() if hasattr(ideal_profile, 'json') else str(ideal_profile)}
    
    Use the provided analysis:
    LinkedIn Analysis: {user_analysis}
    Website Analysis: {website_analysis}
    
    Provide a concise viability assessment focusing on:
    1. Demographic Fit (Industry, Size, Revenue)
    2. Authority (Job Title/Role)
    3. Strategic Alignment
    """
    
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
    
    prompt = f"""
    Identify 3-5 specific, actionable pain points for this lead.
    Look for signals in:
    - LinkedIn Analysis: {user_analysis}
    - Website Analysis: {website_analysis}
    - Hiring Trends: {json.dumps(hiring_data)}
    - Company News: {json.dumps(company_news)}
    
    Focus on challenges related to operational efficiency, AI adoption, or scaling.
    """
    
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
    
    prompt = f"""
    Based on these identified pain points:
    {pain_points}
    
    Map them to Innovize AI's specific solutions described here:
    {company_context}
    
    Propose 2-3 tailored AI/Automation solutions that directly address the pain points.
    Focus on ROI and efficiency gains.
    """
    
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
    
    prompt = f"""
    Craft a personalized outreach strategy.
    
    Intelligence:
    - Profile Insights: {user_analysis}
    - Recent Engagements: {json.dumps(engagements)}
    - Proposed Solutions: {solutions}
    
    Deliver:
    1. A 'Hook': A personalized opening based on a specific achievement or recent post.
    2. A LinkedIn Message: Concise (under 300 characters).
    3. A Hyper-personalized Email: Focus on the 'Value-First' approach, avoiding generic greetings.
    """
    
    messages = [
        SystemMessage(content="You are a high-performance sales copywriter."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"personalized_outreach": response.content}
