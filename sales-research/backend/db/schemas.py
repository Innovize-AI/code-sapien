from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ResearchReportBase(BaseModel):
    linkedin_url: Optional[str] = None
    email_id: Optional[str] = None
    website: Optional[str] = None
    fullname: Optional[str] = None
    profile_picture_url: Optional[str] = None

    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_industries: Optional[str] = None # JSON string
    company_stats: Optional[str] = None      # JSON string

    sales_research_report: Optional[str] = None
    viability_analysis: Optional[str] = None
    lead_score_analysis: Optional[str] = None
    user_profile_analysis: Optional[str] = None
    website_analysis: Optional[str] = None
    cso_strategic_briefing: Optional[str] = None
    
    # Modular Nodules
    target_pain_points: Optional[str] = None
    strategic_solutions: Optional[str] = None
    personalized_outreach: Optional[str] = None
    follow_up_strategy: Optional[str] = None
    buyer_journey_analysis: Optional[str] = None
    meeting_notes: Optional[str] = None
    
    # LinkedIn Subgraph Data
    post_engagements: Optional[str] = None # JSON string
    company_news: Optional[str] = None     # JSON string
    hiring_data: Optional[str] = None      # JSON string
    lead_company_linkedin_url: Optional[str] = None
    lead_li_urn: Optional[str] = None

    lead_score: Optional[int] = None
    project_urgency: Optional[int] = None
    
    # Ownership & Context
    created_by_id: Optional[UUID] = None
    icp_context: Optional[str] = None # JSON snapshot
    
    email_history: Optional[str] = None  # JSON string
    intent_analysis: Optional[str] = None  # JSON string
    extra_metadata: Optional[str] = None   # JSON string


class ResearchReportCreate(ResearchReportBase):
    pass

class LeadSubmissionBase(BaseModel):
    email: str
    linkedin_url: Optional[str] = None
    source: str
    payload: Optional[str] = None
    action_type: Optional[str] = "form_submission"
    action_metadata: Optional[str] = None
    external_form_id: Optional[str] = None
    external_form_name: Optional[str] = None
    rep_id: Optional[UUID] = None # Attribution

class LeadSubmissionCreate(LeadSubmissionBase):
    pass

class LeadSubmission(LeadSubmissionBase):
    id: UUID
    created_at: datetime
    processed_at: Optional[datetime] = None
    research_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class ResearchReport(ResearchReportBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ICP Schemas
class IdealProfileData(BaseModel):
    industry: str
    company_size: Optional[str] = None
    revenue: Optional[str] = None
    job_title: str
    value_proposition: Optional[str] = None

class ProductConfig(BaseModel):
    name: str = Field(description="Name of the product or service")
    description: str = Field(description="Short description for the AI")
    is_strategic_pivot: bool = Field(default=False, description="Is this the 'Hero Product' to pivot to?")
    target_roles: List[str] = Field(default_factory=list, description="Job titles that qualify for this pivot (e.g. 'Founder')")
    relevant_files: List[str] = Field(default_factory=list, description="List of file paths relevant to this product")
    rag_context: Optional[str] = None # Deprecated, kept for backward compatibility if needed

class SellingProfileConfig(BaseModel):
    company_name: str = "Innovize AI"
    description: str = "AI Automation and Sales Intelligence"
    products: List[ProductConfig] = Field(default_factory=list)


class IntegrationSettings(BaseModel):
    tavily_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    user_linkedin_url: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    email_config: Optional[str] = None
    integrations_config: Optional[str] = None
    kit_api_key: Optional[str] = None
    kit_api_secret: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    slack_user_id: Optional[str] = None
    
    # HubSpot
    hubspot_access_token: Optional[str] = None
    hubspot_sync_enabled: bool = False
    
    # Discovery Configs
    discovery_keywords: Optional[str] = None
    apollo_search_config: Optional[str] = None



class OrganizationSettingsBase(BaseModel):
    icp_json: Optional[str] = None
    selling_profile_json: Optional[str] = None
    
    tavily_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    user_linkedin_url: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    email_config: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    
    hubspot_access_token: Optional[str] = None
    hubspot_sync_enabled: Optional[bool] = False

    crm_config: Optional[str] = None
    integrations_config: Optional[str] = None
    onboarding_complete: Optional[int] = 0
    
    discovery_keywords: Optional[str] = None
    apollo_search_config: Optional[str] = None


class OrganizationSettingsCreate(OrganizationSettingsBase):
    pass

class OrganizationSettings(OrganizationSettingsBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Competitor Schemas
class CompetitorBase(BaseModel):
    name: Optional[str] = None
    linkedin_url: str
    created_by_id: Optional[UUID] = None

class CompetitorCreate(CompetitorBase):
    pass

class Competitor(CompetitorBase):
    id: UUID
    created_at: datetime
    creator_name: Optional[str] = None # For UI display

    class Config:
        from_attributes = True

class IdentifiedProfileBase(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    linkedin_url: str
    
    # Classification
    is_fit: bool = False
    is_competitor: bool = False
    is_decision_maker: bool = False
    fit_reasoning: Optional[str] = None
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    
    comment_history: Optional[str] = None
    source_posts: Optional[str] = None
    interaction_history: Optional[str] = None
    profile_metadata: Optional[str] = None
    created_by_id: Optional[UUID] = None

class IdentifiedProfileCreate(IdentifiedProfileBase):
    pass

class IdentifiedProfile(IdentifiedProfileBase):
    id: UUID
    created_at: datetime
    last_interaction_at: Optional[datetime] = None
    latest_report_id: Optional[UUID] = None  # New field for linking

    class Config:
        from_attributes = True

class ActivityBase(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    metadata_json: Optional[str] = None
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    created_by_id: Optional[UUID] = None

class ActivityCreate(ActivityBase):
    pass

class Activity(ActivityBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Autopilot Rule Schemas
class AutopilotRuleBase(BaseModel):
    type: str # 'keyword', 'apollo_config'
    value: str
    is_active: bool = True
    organization_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None

class AutopilotRuleCreate(AutopilotRuleBase):
    pass

class AutopilotRule(AutopilotRuleBase):
    id: UUID
    created_at: datetime
    creator_name: Optional[str] = None # For UI display

    class Config:
        from_attributes = True

# User Settings Schemas
class UserSettingsBase(BaseModel):
    user_linkedin_url: Optional[str] = None
    email_config: Optional[str] = None
    icp_json: Optional[str] = None
    slack_user_id: Optional[str] = None

class UserSettingsCreate(UserSettingsBase):
    user_id: UUID

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettings(UserSettingsBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
