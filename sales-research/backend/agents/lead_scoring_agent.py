from langchain_core.messages import SystemMessage, HumanMessage
import json
from workflow.state import AgentState
from prompts.sales_prompts import LEAD_SCORER_SYSTEM_PROMPT, LEAD_DATA_EXTRACTOR_PROMPT
from models.openai_models import get_open_ai
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

class CategoricalScore(BaseModel):
    score: int = Field(description="Numerical score for this category")
    reasoning: str = Field(description="Specific, evidence-based reason for this score (e.g., 'CTO at a 500-employee tech firm', '3 website visits and 1 demo request')")

class LeadScoreBreakdown(BaseModel):
    demographic_fit: CategoricalScore = Field(description="Score and reasoning for Industry, Company Size, Revenue, Job Title")
    engagement: CategoricalScore = Field(description="Score and reasoning for Website Visits, Content Interaction, Demo Request, Social Media")
    sales_readiness: CategoricalScore = Field(description="Score and reasoning for Buying Stage, Recent Activity")
    lead_source: CategoricalScore = Field(description="Score and reasoning for Referral, Inbound Marketing, Paid Ads, Cold Outreach")
    timing: CategoricalScore = Field(description="Score and reasoning for Purchase Timeline, Project Urgency")

class LeadScoreAnalysis(BaseModel):
    total_score: int = Field(description="The final calculated lead score.")
    score_breakdown: LeadScoreBreakdown = Field(description="Detailed breakdown of scores for each category.")
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
    
    # Bundle research into a structured description for the extractor
    research_context = {
        "user_profile": user_analysis_dict,
        "website_intelligence": website_analysis_dict,
        "company_metrics": company_stats,
        "interaction_history": email_history,
        "input_metadata": input_lead_data.model_dump() if hasattr(input_lead_data, 'model_dump') else input_lead_data
    }

    messages = [
        SystemMessage(content=LEAD_DATA_EXTRACTOR_PROMPT),
        HumanMessage(content=f"EXTRACT LEAD DATA FROM RESEARCH: {json.dumps(research_context)}")
    ]

    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0)
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
        HumanMessage(content=f"SCORE THIS LEAD PROFILE: {json.dumps(lead_extracted_dict)}")
    ]

    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0)
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
