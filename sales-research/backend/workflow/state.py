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
    industry: Union[str, List[str]] = Field(..., description="Target industries for the Ideal Customer Profile (ICP)")
    company_size: Optional[Union[str, List[str]]] = Field(..., description="Target company sizes or employee counts for the ICP")
    revenue: Optional[Union[str, List[str]]] = Field(None, description="Target annual revenues for the ICP")
    job_title: Union[str, List[str]] = Field(..., description="Target job titles or roles for the ICP")

class Product(BaseModel):
    name: str
    description: str
    target_pain_points: List[str]
    is_strategic_pivot: bool = False
    target_roles: List[str] = []
    rag_context: Optional[str] = None


class SellingCompanyProfile(BaseModel):
    name: str
    description: str
    products: List[Product]

class InputLeadData(BaseModel):
    lead_source: Optional[str] = None
    download_marketing_material: Optional[bool] = None
    demo_requested: Optional[bool] = None
    referral_partner_introduction: Optional[bool] = None
    project_urgency: Optional[int] = None
    refresh: bool = False
    
    # Discovery Context (New)
    discovery_source: Optional[str] = None # 'competitor_comment', 'keyword_search', 'form_fill'
    discovery_context: Optional[dict] = None # { "comment": "...", "post_url": "...", "keyword": "..." }
    
    extra_metadata: Optional[dict] = None # For webhook/form extras
    trigger_context: Optional[str] = None # 'email_update', 'crm_update'
    
    # Enrichment Fields (Deterministic)
    industry: Optional[str] = None
    employee_size: Optional[str] = None
    revenue: Optional[str] = None

class AgentState(TypedDict):
    email_id: str
    linkedin_url: str
    website: str
    ideal_profile: IdealProfile
    selling_company_profile: SellingCompanyProfile
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
    discovery_interaction_history: Annotated[List[dict], reduce_last]
    crm_context: Annotated[Optional[dict], reduce_last]

    # Apollo Rich Metadata (from waterfall enrichment)
    company_metadata: Annotated[Optional[dict], reduce_last]


    # Specialized Nodules

    target_pain_points: Annotated[Union[dict, str], reduce_last]
    strategic_rag_briefing: Annotated[str, reduce_last]
    lead_segment: Annotated[str, reduce_last] # new field
    strategic_solutions: Annotated[Union[dict, str], reduce_last]
    personalized_outreach: Annotated[dict, reduce_last]
    follow_up_strategy: Annotated[Union[dict, str], reduce_last]
    viability_analysis: Annotated[str, reduce_last]
    cso_strategic_briefing: Annotated[dict, reduce_last]
    signal_leverage_score: Annotated[int, reduce_last]
    is_strategic_pivot_fit: Annotated[bool, reduce_last]
    pivot_product_name: Annotated[str, reduce_last]
    campaign_outreach_variants: Annotated[List[dict], reduce_last]


