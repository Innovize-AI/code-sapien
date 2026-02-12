from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from prompts.sales_prompts import (
    PAIN_POINT_DISCOVERY_PROMPT, 
    STRATEGIC_SOLUTION_PROMPT, 
    OUTREACH_DESIGN_PROMPT
)
import json
from models.structured_output import OutreachStrategy
from pydantic import BaseModel, Field
from typing import List
from services.knowledge_service import KnowledgeService

# Initialize KnowledgeService
knowledge_service = KnowledgeService(index_name="glial-index")


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


class PainPointAnalysis(BaseModel):
    summary: str = Field(description="High-level overview of identified challenges.")
    points: List[str] = Field(description="Specific, individual pain points discovered.")
    impact: str = Field(description="The potential business impact if these are not addressed.")

class StrategicSolutionProposal(BaseModel):
    summary: str = Field(description="Overview of the proposed transformation.")
    solutions: List[str] = Field(description="Specific AI/Service solutions proposed.")
    value_proposition: str = Field(description="The core value delivered by these solutions.")

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
        SystemMessage(content="You are an expert business analyst specializing in B2B pain point identification. You look for deeper organizational struggles, not just surface issues."),
        HumanMessage(content=prompt)
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(PainPointAnalysis)
        response = structured_llm.invoke(messages)
        return {"target_pain_points": response.model_dump() if response else {}}
    except Exception as e:
        print(f"Error in pain_point_node: {e}")
        return {"target_pain_points": {}}

def solution_node(state: AgentState):
    """Maps identified pain points to Innovize AI's specific offerings using verified RAG intelligence."""
    pain_points_dict = state.get("target_pain_points", {})
    pain_points_str = json.dumps(pain_points_dict)
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    selling_profile = state.get("selling_company_profile")
    
    # Defaults for backward compatibility
    selling_company_name = selling_profile.name if selling_profile else "Innovize AI"
    selling_company_context = f"{selling_company_name} specializes in {selling_profile.description if selling_profile else 'AI automation'}."
    
    # Build mapping logic string
    if selling_profile:
        mapping_logic = "\n".join([f"    - If {', '.join(p.target_pain_points)} -> Use **{p.name}**." for p in selling_profile.products])
    else:
        mapping_logic = "- If Sales -> Use Glial.\n    - If Logistics -> Use IDP.\n    - If Internal -> Use Agentic KB."

    rag_briefing = state.get("strategic_rag_briefing", "No RAG context available.")
    
    # Build the Prompt with Agentic RAG context
    prompt = STRATEGIC_SOLUTION_PROMPT.format(
        pain_points=pain_points_str,
        lead_segment=lead_segment,
        selling_company_name=selling_company_name,
        selling_company_context=selling_company_context,
        solution_context=rag_briefing,
        selling_mapping_logic=mapping_logic
    )

    messages = [
        SystemMessage(content=f"You are a Senior AI Solutions Architect for {selling_company_name}. Your task is to transform discovered pain points into high-impact AI solutions."),
        HumanMessage(content=f"STRATEGIC RAG BRIEFING: {rag_briefing}\n\nPROMPT: {prompt}")
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-pro-preview", temperature=0)
        structured_llm = model.with_structured_output(StrategicSolutionProposal)
        response = structured_llm.invoke(messages)
        return {"strategic_solutions": response.model_dump() if response else {}}
    except Exception as e:
        print(f"Error in solution_node: {e}")
        return {"strategic_solutions": {}}

def outreach_node(state: AgentState):
    """Crafts the personalized "hook" and outbound message using structured output."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)
    solutions = state.get("strategic_solutions", "")
    engagements = state.get("post_engagements", [])
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    
    journey_analysis = state.get("buyer_journey_analysis", {})
    cso_briefing = state.get("cso_strategic_briefing", {})

    prompt = OUTREACH_DESIGN_PROMPT.format(
        user_analysis=user_analysis,
        lead_segment=lead_segment,
        engagements=json.dumps(engagements),
        solutions=solutions,
        journey_context=json.dumps(journey_analysis),
        cso_context=json.dumps(cso_briefing)
    )

    messages = [
        SystemMessage(content="### ROLE: You are a world-class direct response copywriter and cold email strategist."),
        HumanMessage(content=prompt)
    ]
    
    model = get_gemini_model(model="gemini-3-pro-preview", temperature=0).with_structured_output(OutreachStrategy)
    response = model.invoke(messages)
    
    return {"personalized_outreach": response.model_dump()}
