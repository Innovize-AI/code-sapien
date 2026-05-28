from models.structured_output_cso import MultiOutreachSequence
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from datetime import datetime
from prompts.sales_prompts import (
    PAIN_POINT_DISCOVERY_PROMPT, 
    STRATEGIC_SOLUTION_PROMPT, 
    OUTREACH_DESIGN_PROMPT
)
import json
from models.structured_output import OutreachStrategy, Solution, StrategicSolutions
from models.structured_output_cso import OutreachSequence
from pydantic import BaseModel, Field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)





# No global knowledge_service - must be resolved per-request


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
    solutions: List[Solution] = Field(description="Specific AI/Service solutions proposed with Logical Gap Mapping.")
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
        logger.error(f"Error in pain_point_node: {e}")
        return {"target_pain_points": {}}


def strategic_solution_synthesizer_node(state: AgentState):
    """
    Synthesizes the research_solution_pool into the structured strategic_solutions field.
    This ensures the frontend receives the data in the high-fidelity format it expects.
    """
    solution_pool = state.get("research_solution_pool", [])
    if not solution_pool:
        logger.info("Synthesizer: No research solution pool found. Skipping.")
        return {"strategic_solutions": []}

    target_pain_points = state.get("target_pain_points", {})
    selling_profile = state.get("selling_company_profile")
    selling_company_name = getattr(selling_profile, "company_name", "Our Company") if selling_profile else "Our Company"
    business_model = getattr(selling_profile, "business_model", "product") if selling_profile else "product"
    
    # Context summary for the prompt
    selling_company_context = f"Business Model: {business_model}"
    
    # We pass the entire pool as the context
    pool_str = ""
    for idx, p in enumerate(solution_pool):
        if not isinstance(p, dict): continue
        pool_str += f"\nPRODUCT {idx+1}: {p.get('product_name')}\n"
        pool_str += f"TECHNICAL: {p.get('technical_intel')}\n"
        pool_str += f"NARRATIVE: {p.get('narrative_intel')}\n"
        pool_str += f"COLLATERAL: {p.get('collateral_intel')}\n"
        pool_str += f"OBJECTIONS: {p.get('objections')}\n"

    prompt = STRATEGIC_SOLUTION_PROMPT.format(
        pain_points=json.dumps(target_pain_points),
        lead_segment=state.get("lead_segment", "POTENTIAL_CLIENT"),
        selling_company_name=selling_company_name,
        business_model=business_model,
        selling_company_context=selling_company_context,
        solution_context=pool_str
    )

    messages = [
        SystemMessage(content="You are a Strategic Solution Architect. Your mission is to map RAG intelligence to specific prospect pain points with high-fidelity 'Logical Gap Mapping'."),
        HumanMessage(content=prompt)
    ]

    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(StrategicSolutions)
        response = structured_llm.invoke(messages)
        
        if not response or not response.solutions:
            return {"strategic_solutions": []}
            
        # Convert to list of dicts for state/persistence
        solutions_list = [s.model_dump() for s in response.solutions]
        logger.info(f"Synthesizer: Successfully generated {len(solutions_list)} strategic solutions.")
        return {"strategic_solutions": solutions_list}
        
    except Exception as e:
        logger.error(f"Error in strategic_solution_synthesizer_node: {e}", exc_info=True)
        return {"strategic_solutions": []}



def outreach_node(state: AgentState):
    """Crafts the personalized "hook" and outbound message using structured output."""
    user_analysis_dict = state.get("user_profile_analysis", {})
    user_analysis = format_profile_analysis(user_analysis_dict)
    
    # Context from CSO
    cso_briefing = state.get("cso_strategic_briefing", {})
    selected_product = cso_briefing.get("selected_product_name", "Our Solution")
    
    engagements = state.get("post_engagements", [])
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    
    # Dynamically derive persona
    selling_profile = state.get("selling_company_profile")
    selling_company_name = getattr(selling_profile, "company_name", "Our Company") if selling_profile else "Our Company"

    # Extract lookalike_peer from CSO briefing
    lookalike_peer = cso_briefing.get("lookalike_peer", "N/A")

    prompt = OUTREACH_DESIGN_PROMPT.format(
        user_analysis=user_analysis,
        lead_segment=lead_segment,
        lookalike_peer=lookalike_peer,
        solutions=f"PRODUCT SELECTED BY CSO: {selected_product}\nJUSTIFICATION: {cso_briefing.get('selected_product_justification')}",
        cso_context=json.dumps(cso_briefing),
        current_date=datetime.now().strftime("%A, %B %d, %Y")
    )

    # Add RAG Instruction (The "Winning Intel" passed from CSO)
    rag_briefing = state.get("strategic_rag_briefing", "No RAG context available.")
    prompt += f"""
### STRATEGIC RAG BRIEFING (THE WINNING INTEL):
{rag_briefing}
"""

    messages = [
        SystemMessage(content="""You are a world-class Direct Response Copywriter and Strategic Sales Consultant. 
        Your mission is to craft outreach that is authentic, evidence-based, and completely free of generic AI terminology.
        You rely strictly on the provided 'Strategic RAG Briefing' to ground your claims.
        """),
        HumanMessage(content=prompt)
    ]

    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0.2)
        # The Outreach Designer takes the CSO's Blueprints and returns the fully populated Sequences
        structured_llm = model.with_structured_output(MultiOutreachSequence)
        response = structured_llm.invoke(messages)
        
        if not response or not response.sequences:
            logger.warning("Strategy Agent: Model returned empty or null sequences. Check CSO context and prompt grounding.")
            return {
                "final_outreach_sequences": [],
                "personalized_outreach": [], 
                "campaign_outreach_variants": []
            }
        
        all_sequences_dict = [s.model_dump() for s in response.sequences]
        logger.info(f"Strategy Agent: Successfully generated {len(all_sequences_dict)} outreach sequences.")
        
        return {
            "final_outreach_sequences": all_sequences_dict,
            "personalized_outreach": all_sequences_dict, # Sync for legacy persistence fallback
        }
        
    except Exception as e:
        logger.error(f"Error in outreach_node: {e}", exc_info=True)
        return {
            "final_outreach_sequences": [],
            "personalized_outreach": [],
        }
