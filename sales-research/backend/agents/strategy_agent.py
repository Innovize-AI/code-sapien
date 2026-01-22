from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.openai_models import get_open_ai
from prompts.sales_prompts import (
    PAIN_POINT_DISCOVERY_PROMPT, 
    STRATEGIC_SOLUTION_PROMPT, 
    OUTREACH_DESIGN_PROMPT
)
import json


def format_profile_analysis(analysis: dict) -> str:
    """Helper to convert structured LinkedInAnalysis dict to markdown string for LLM prompts."""
    # ... (existing content)
    if not analysis or not isinstance(analysis, dict):
        return str(analysis)
    
    md = f"""
PROFILE SUMMARY:
{analysis.get('profile_summary', 'N/A')}

STRATEGIC ROLE FIT:
{analysis.get('strategic_role_fit', 'N/A')}

COMPANY SIGNALS:
{analysis.get('company_signals', 'N/A')}

ENGAGEMENT PERSONA:
{analysis.get('engagement_persona', 'N/A')}

PAIN POINT HYPOTHESIS:
{analysis.get('pain_point_hypothesis', 'N/A')}

RECENT POSTS:
"""
    for post in analysis.get('posts_analysis', []):
        md += f"- {post.get('post_title')} ({post.get('posted_date')}): {post.get('summary')} [URL: {post.get('post_url')}]\n"
    
    return md

def format_website_analysis(analysis: dict) -> str:
    """Helper to convert structured WebsiteAnalysis dict to markdown string for LLM prompts."""
    if not analysis or not isinstance(analysis, dict):
        return str(analysis)
        
    md = f"""
OVERVIEW:
{analysis.get('summary', 'N/A')}

INDUSTRY:
{analysis.get('industry', 'N/A')}

TARGET AUDIENCE:
{analysis.get('target_audience', 'N/A')}

OFFERINGS:
{", ".join(analysis.get('core_offerings', []))}

INDUSTRY PAIN POINTS:
{", ".join(analysis.get('industry_pain_points', []))}

COMPETITIVE ADVANTAGE:
{analysis.get('competitive_advantage', 'N/A')}
"""
    return md


def pain_point_node(state: AgentState):
    """Identifies specific, actionable pain points from the lead's profile and company footprint."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)
    website_analysis_dict = state.get("website_analysis", {})
    website_analysis = format_website_analysis(website_analysis_dict)
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
        SystemMessage(content="You are a Senior AI Solutions Architect and Value Engineer. Your task is to transform discovered pain points into high-impact, transformative AI solutions."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"strategic_solutions": response.content}

def outreach_node(state: AgentState):
    """Crafts the personalized "hook" and outbound message."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)
    solutions = state.get("strategic_solutions", "")
    engagements = state.get("post_engagements", [])
    journey_analysis = state.get("buyer_journey_analysis", {})
    
    prompt = OUTREACH_DESIGN_PROMPT.format(
        user_analysis=user_analysis,
        engagements=json.dumps(engagements),
        solutions=solutions,
        journey_context=json.dumps(journey_analysis)
    )

    
    messages = [
        SystemMessage(content="You are a high-performance sales copywriter."),
        HumanMessage(content=prompt)
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"personalized_outreach": response.content}
