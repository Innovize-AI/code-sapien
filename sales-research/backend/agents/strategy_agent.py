import logging
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from models.gemini_models import get_gemini_model
from prompts.sales_prompts import (
    PAIN_POINT_DISCOVERY_PROMPT, 
    STRATEGIC_SOLUTION_PROMPT, 
    OUTREACH_DESIGN_PROMPT
)
import json
from models.structured_output import OutreachStrategy, CampaignVariant, Solution, StrategicSolutions
from pydantic import BaseModel, Field
from typing import List

logger = logging.getLogger(__name__)
from services.knowledge_service import KnowledgeService

class MultiCampaignResponse(BaseModel):
    variants: List[CampaignVariant] = Field(description="List of distinct outreach campaigns (e.g., Best Fit vs Strategic Pivot).")


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

def solution_node(state: AgentState):
    """Maps identified pain points to Innovize AI's specific offerings using verified RAG intelligence."""
    pain_points_dict = state.get("target_pain_points", {})
    pain_points_str = json.dumps(pain_points_dict)
    lead_segment = state.get("lead_segment", "POTENTIAL_CLIENT")
    selling_profile = state.get("selling_company_profile")
    
    # Defaults for backward compatibility
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    selling_company_context = f"{selling_company_name} specializes in {getattr(selling_profile, 'description', 'AI automation') if selling_profile else 'AI automation'}."
    
    # Build mapping logic string
    if selling_profile:
        # Use description for dynamic mapping since target_pain_points is not in schema
        mapping_logic = "\n".join([f"    - If needs relate to '{getattr(p, 'description', '')}' -> Use **{p.name}**." for p in selling_profile.products])
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
    
    # Inject Pivot Context if Fit
    if state.get("is_strategic_pivot_fit"):
        pivot_name = state.get("pivot_product_name")
        prompt += f"\n\nIMPORTANT: The lead has been identified as a STRICT FIT for the Strategic Pivot Product: '{pivot_name}'.\nYou MUST include a solution mapping that leverages '{pivot_name}' as a primary or alternative option."


    messages = [
        SystemMessage(content=f"You are a Senior AI Solutions Architect for {selling_company_name}. Your task is to transform discovered pain points into high-impact AI solutions."),
        HumanMessage(content=f"STRATEGIC RAG BRIEFING: {rag_briefing}\n\nPROMPT: {prompt}")
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(StrategicSolutionProposal)
        response = structured_llm.invoke(messages)
        return {"strategic_solutions": response.model_dump() if response else {}}
    except Exception as e:
        logger.error(f"Error in solution_node: {e}")
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
    
    # Determine if we need multi-campaign generation
    is_pivot_fit = state.get("is_strategic_pivot_fit", False)
    pivot_name = state.get("pivot_product_name", "")
    
    if is_pivot_fit:
        prompt += f"""

TASK MODIFICATION: You MUST generate EXACTLY TWO distinct campaign variants:
Variant 1: "Best Fit - [Product Name]" -> The standard approach based on strongest pain points.
Variant 2: "Strategic Pivot - {pivot_name}" -> A campaign specifically pitching '{pivot_name}' as the solution, using the RAG context provided.
"""
    else:
        prompt += """

TASK MODIFICATION: You MUST generate EXACTLY ONE campaign variant:
Variant 1: "Best Fit - [Product Name]" -> The standard approach based on strongest pain points.
DO NOT generate a second variant.
"""

    messages = [
        SystemMessage(content="### ROLE: You are a world-class direct response copywriter and cold email strategist."),
        HumanMessage(content=prompt)
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0.2) # Slightly higher temp for creativity
        structured_llm = model.with_structured_output(MultiCampaignResponse)
        response = structured_llm.invoke(messages)
        
        variants = response.variants if response else []
        
        # Fallback if empty or failed - Construct a default variant from legacy parsing if possible, or just fail gracefully
        if not variants:
            # Attempt to rescue by asking for a single non-structured response? 
            # For now, let's just ensure we return what we have or empty.
            # But better: if we have a legacy path, we could wrap it. 
            # Since we are enforcing structured output, let's trust it or return empty.
            return {"personalized_outreach": [], "campaign_outreach_variants": []}

        # Select primary (Best Fit) for backward compatibility
        primary_variant = variants[0]
        # Attempt to find 'Best Fit' or use first
        for v in variants:
            if "Best Fit" in v.variant_name:
                primary_variant = v
                break
        
        # Convert all variants to dict for storage
        variant_dicts = [v.model_dump() for v in variants]
        
        # ALWAYS return the variants list in personalized_outreach
        return {
            "personalized_outreach": variant_dicts,
            "campaign_outreach_variants": variant_dicts
        }

    except Exception as e:
        logger.error(f"Error in outreach_node: {e}")
        return {"personalized_outreach": [], "campaign_outreach_variants": []}


