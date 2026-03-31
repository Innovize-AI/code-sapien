from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
from workflow.state import AgentState
from prompts.sales_prompts import LEAD_SCORER_SYSTEM_PROMPT, LEAD_DATA_EXTRACTOR_PROMPT
from models.gemini_models import get_gemini_model
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class ExtractedLeadData(BaseModel):
    industry: str = Field(description="The industry of the lead's company")
    company_size: str = Field(description="The size or number of employees of the lead's company")
    revenue: str = Field(description="The annual revenue of the lead's company")
    job_title: str = Field(description="The job title/role of the lead")
    website_visits: int = Field(description="Number of times the lead has visited the website")
    high_value_page_interaction: bool = Field(description="Whether the lead interacted with high-value pages")
    content_interaction: str = Field(description="Details of any content interaction (webinars, eBooks, etc.)")
    demo_request: bool = Field(description="Whether the lead has requested a demo or filled a contact form")
    social_media_engagement: str = Field(description="Details of social media interactions")
    recent_activity: str = Field(description="Summary of recent engagement activity")
    buying_stage: str = Field(description="Current stage in the buyer journey (Awareness, Consideration, Decision)")
    referral_source: str = Field(description="How the lead was generated (Referral, Inbound, etc.)")
    purchase_timeline: str = Field(description="Estimated timeline for purchase")
    project_urgency: str = Field(description="Level of urgency for the project (High, Medium, Low)")
    discovery_insights: str = Field(description="Analysis of HOW the lead was found (e.g., intent behind their competitor comment, relevance of search keywords). patterns detected.")
    
    # Negative/Cold Signal Handling
    negative_signals: List[str] = Field(default=[], description="List of specific negative signals found (e.g., 'Competitor Lock-in', 'Hostile Reply', 'Closed Lost - Product Gap', 'Unsubscribe Request').")
    is_cold: bool = Field(default=False, description="TRUE if the lead has explicitly rejected us, unsubscribed, or is a 'Closed Lost' deal with no chance of recovery.")

class CategoricalScore(BaseModel):
    score: int = Field(description="Numerical score for this category")
    reasoning: str = Field(description="Specific, evidence-based reason for this score (e.g., 'CTO at a 500-employee tech firm', '3 website visits and 1 demo request')")

class LeadScoreBreakdown(BaseModel):
    firmographic_fit: CategoricalScore = Field(description="Score and reasoning for Industry Match, Company Size/Scale, and Revenue/Growth Stage.")
    persona_alignment: CategoricalScore = Field(description="Score and reasoning for Job Title Seniority, Recent Hiring/News Signals, and Social Activity Level.")
    behavioral_engagement: CategoricalScore = Field(description="Score and reasoning for Lead Magnet Downloads, Demo Requests, and Contact Form fills (Inbound).")
    strategic_intent: CategoricalScore = Field(description="Score and reasoning for Discovery Source (e.g. Competitor Comment), Pain Point Depth, and Partner Referrals (Outbound).")

class LeadScoreAnalysis(BaseModel):
    total_score: int = Field(description="The final calculated lead score.")
    score_breakdown: LeadScoreBreakdown = Field(description="Detailed breakdown of scores for each category.")
    negative_penalty: int = Field(default=0, description="Points deducted due to negative signals (e.g., 50 for is_cold).")
    penalty_reason: str = Field(default="", description="Reason for the penalty (e.g., 'Lead Unsubscribed').")
    analysis: str = Field(description="Detailed reasoning for the assigned score.")
    viability_analysis: str = Field(description="Specific assessment of how well this lead fits the Ideal Customer Profile (ICP).")
    lead_score_recommendations: List[str] = Field(description="Strategic recommendations for next steps.")

def lead_data_extractor(state: AgentState):
    """Summarizes research into a structured lead profile for scoring."""
    user_analysis_dict = state.get('user_profile_analysis', {})
    website_analysis_dict = state.get("website_analysis", {})
    input_lead_data = state["input_lead_data"]
    company_stats = state.get("company_stats", {})
    email_history = state.get("email_history", [])
    post_engagements = state.get("post_engagements", [])
    
    # Bundle research into a structured description for the extractor
    research_context = {
        "user_profile": user_analysis_dict,
        "website_intelligence": website_analysis_dict,
        "company_metrics": company_stats,
        "interaction_history": email_history,
        "current_session_engagements": post_engagements,
        "discovery_interaction_history": state.get("discovery_interaction_history", []),
        "input_metadata": input_lead_data.model_dump() if hasattr(input_lead_data, 'model_dump') else input_lead_data,
        "crm_history": state.get("crm_context")
    }
    
    messages = [
        SystemMessage(content=LEAD_DATA_EXTRACTOR_PROMPT),
        HumanMessage(content=f"EXTRACT LEAD DATA FROM RESEARCH: {json.dumps(research_context)}")
    ]

    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(ExtractedLeadData)
        response = structured_llm.invoke(messages)
        
        if not response:
             return {"lead_extracted_data": {}}
             
        return {"lead_extracted_data": response.model_dump()}
    except Exception as e:
        logger.error(f"Error in lead_data_extractor: {e}")
        return {"lead_extracted_data": {}}

def lead_scorer(state: AgentState):
    """Scores the lead based on the extracted data and ICP."""
    lead_extracted_dict = state.get("lead_extracted_data", {})
    ideal_profile = state["ideal_profile"]
    ideal_profile_json = ideal_profile.model_dump_json() if hasattr(ideal_profile, 'model_dump_json') else str(ideal_profile)

    messages = [
        SystemMessage(content=LEAD_SCORER_SYSTEM_PROMPT.format(content=ideal_profile_json)),
        HumanMessage(content=f"SCORE THIS LEAD PROFILE: {json.dumps(lead_extracted_dict)}. CRM_CONTEXT: {json.dumps(state.get('crm_context') or {})}")
    ]

    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(LeadScoreAnalysis)
        response: LeadScoreAnalysis = structured_llm.invoke(messages)
        
        if not response:
             return {"lead_score_analysis": {}, "viability_analysis": ""}
             
        # Manually verify and fix total_score if LLM math failed
        breakdown = response.score_breakdown
        calculated_total = (
            breakdown.firmographic_fit.score +
            breakdown.persona_alignment.score +
            breakdown.behavioral_engagement.score +
            breakdown.strategic_intent.score
        ) - response.negative_penalty
        
        # Ensure floor of 0 and cap of 100
        calculated_total = max(0, min(100, calculated_total))
        
        if response.total_score != calculated_total:
            logger.warning(f"Fixing LLM lead score math: LLM said {response.total_score}, Calculated {calculated_total}")
            response.total_score = calculated_total

        res_dict = response.model_dump()
        return {
            "lead_score_analysis": res_dict,
            "viability_analysis": res_dict.get("viability_analysis", "")
        }
    except Exception as e:
        logger.error(f"Error in lead_scorer: {e}")
        return {"lead_score_analysis": {}}

class RevalidatedFit(BaseModel):
    is_fit: bool = Field(description="Updated fit status based on new company metrics")
    reasoning: str = Field(description="Concise explanation for the fit status, specifically calling out deviations in headcount, revenue, or industry if they exist.")

async def revalidate_lead_fit_async(lead_data: dict, company_metrics: dict, icp_data: dict | None = None):
    """
    Refines the fit status and reasoning based on confirmed firmographic data (Apollo/RapidAPI).
    If icp_data is provided, it uses the actual organization ICP from the database.
    """
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(RevalidatedFit)
        
        # Use provided ICP or fallback to default
        if icp_data:
             icp_context = f"ICP STRATEGY: {json.dumps(icp_data)}"
        else:
             icp_context = "ICP: B2B SaaS companies, 50-500 employees, series A-D, technology space."
        
        context = {
            "initial_lead_info": {
                "name": lead_data.get("name"),
                "headline": lead_data.get("headline"),
                "initial_fit": lead_data.get("is_fit"),
                "initial_reasoning": lead_data.get("fit_reasoning")
            },
            "new_company_metrics": company_metrics,
            "icp_constraints": icp_context
        }
        
        messages = [
            SystemMessage(content="You are an ICP Validation Agent. Your goal is to refine a lead's fit status based on NEWLY confirmed company firmographic data from Apollo/RapidAPI. \n"
                                  "IMPORTANT: The ICP fields (industry, company_size, revenue, etc.) may be lists of strings. \n"
                                  "A match is confirmed if the company's metrics align with ANY of the provided values in those lists. \n"
                                  "Do not simply discard the 'initial_reasoning' provided in the context. \n"
                                  "Instead, **MERGE** the discovery insights with the new firmographic facts. \n"
                                  "A final reasoning should look like: '[Initial discovery context] + [Firmographic confirmation or rejection]'. \n"
                                  "If the new metrics cause a change in status, explain exactly which metric overrode the initial fit."),
            HumanMessage(content=f"RE-VALIDATE THIS LEAD: {json.dumps(context)}")
        ]
        
        response: RevalidatedFit = await structured_llm.ainvoke(messages)
        if response:
            return response.is_fit, response.reasoning
        return lead_data.get("is_fit"), lead_data.get("fit_reasoning")
    except Exception as e:
        logger.error(f"Error in revalidate_lead_fit_async: {e}")
        return lead_data.get("is_fit"), lead_data.get("fit_reasoning")
