from typing import Annotated, TypedDict, Optional, List, Union
import operator

def reduce_dict(left: dict, right: Union[dict, List[dict]]) -> dict:
    """Merges dictionaries. Handles single dict or list of dicts (parallel updates)."""
    if left is None:
        left = {}
    if not isinstance(left, dict):
        left = {}

    if isinstance(right, list):
        new_dict = left.copy()
        for item in right:
             if isinstance(item, dict):
                 new_dict.update(item)
        return new_dict

    if not isinstance(right, dict):
        right = {}
    return {**left, **right}

def reduce_last(left: any, right: any):
    """Reducer that always takes the latest value. Handles list of updates from parallel nodes."""
    if isinstance(right, list):
        if not right:
            return left
        return right[-1]
    return right

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
    user_profile_details: Annotated[dict, reduce_dict]
    scraped_website_content: Annotated[str, operator.add]
    user_profile_analysis: Annotated[dict, reduce_dict]
    website_analysis: Annotated[dict, reduce_last]
    lead_extracted_data: Annotated[dict, reduce_last]
    sales_research_report: Annotated[Union[dict, str], reduce_last]
    company_context: str
    lead_score_analysis: Annotated[dict, reduce_last]
    email_history: List[dict]
    meeting_notes: str
    intent_analysis: dict
    buyer_journey_analysis: Annotated[dict, reduce_last]
    fullname: Optional[str]
    profile_picture_url: Optional[str]
    lead_li_urn: Optional[str]
    extra_research_context: Optional[dict]
    
    # LinkedIn Subgraph Data
    post_engagements: List[dict]
    company_news: List[dict]
    hiring_data: List[dict]
    user_linkedin_url: Optional[str]
    company_linkedin_url: Optional[str]
    lead_company_linkedin_url: Annotated[Optional[str], reduce_last]
    company_name: Annotated[Optional[str], reduce_last]
    company_description: Annotated[Optional[str], reduce_last]
    company_industries: Annotated[Optional[List[str]], reduce_last]
    company_stats: Annotated[Optional[dict], reduce_last]


    # Specialized Nodules

    target_pain_points: Annotated[Union[dict, str], reduce_last]
    strategic_solutions: Annotated[Union[dict, str], reduce_last]
    personalized_outreach: Annotated[dict, reduce_last]
    follow_up_strategy: Annotated[Union[dict, str], reduce_last]
    viability_analysis: Annotated[str, reduce_last]
