from typing import Annotated, TypedDict, Optional, List
import operator
from pydantic import BaseModel, Field

class IdealProfile(BaseModel):
    industry: str = Field(..., description="Industry of the lead's company")
    company_size: Optional[str] = Field(..., description="Number of employees in the lead's company")
    revenue: Optional[str] = Field(None, description="Annual revenue of the lead's company in millions")
    job_title: str = Field(..., description="Job title of the lead")

class InputLeadData(BaseModel):
    lead_source: Optional[str] = None
    download_marketing_material: Optional[bool] = None
    demo_requested: Optional[bool] = None
    referral_partner_introduction: Optional[bool] = None
    project_urgency: Optional[int] = None
    refresh: bool = False
    extra_metadata: Optional[dict] = None # For webhook/form extras

class AgentState(TypedDict):
    email_id: str
    linkedin_url: str
    website: str
    ideal_profile: IdealProfile
    input_lead_data: InputLeadData
    user_profile_details: Annotated[str, operator.add]
    scraped_website_content: Annotated[str, operator.add]
    user_profile_analysis: Annotated[str, operator.add]
    website_analysis: Annotated[str, operator.add]
    lead_extracted_data: Annotated[str, operator.add]
    sales_research_report: Annotated[str, operator.add]
    company_context: str
    lead_score_analysis: Annotated[str, operator.add]
    email_history: List[dict]
    intent_analysis: dict
    fullname: Optional[str]
    profile_picture_url: Optional[str]
    extra_research_context: Optional[dict]
    
    # LinkedIn Subgraph Data
    post_engagements: List[dict]
    company_news: List[dict]
    hiring_data: List[dict]
    user_linkedin_url: Optional[str]
    company_linkedin_url: Optional[str]

    # Specialized Nodules

    viability_analysis: Annotated[str, operator.add]
    target_pain_points: Annotated[str, operator.add]
    strategic_solutions: Annotated[str, operator.add]
    personalized_outreach: Annotated[str, operator.add]
