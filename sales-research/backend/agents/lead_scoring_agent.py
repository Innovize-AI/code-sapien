from langchain_core.messages import SystemMessage, HumanMessage
import json
from workflow.state import AgentState
from prompts.sales_prompts import LEAD_SCORER_SYSTEM_PROMPT, LEAD_DATA_EXTRACTOR_PROMPT
from models.gemini_models import get_gemini_model
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

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
        print(f"Error in lead_data_extractor: {e}")
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
        response = structured_llm.invoke(messages)
        
        if not response:
             return {"lead_score_analysis": {}, "viability_analysis": ""}
             
        res_dict = response.model_dump()
        return {
            "lead_score_analysis": res_dict,
            "viability_analysis": res_dict.get("viability_analysis", "")
        }
    except Exception as e:
        print(f"Error in lead_scorer: {e}")
        return {"lead_score_analysis": {}}
