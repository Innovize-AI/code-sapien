from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ResearchReportBase(BaseModel):
    linkedin_url: Optional[str] = None
    email_id: Optional[str] = None
    website: Optional[str] = None
    fullname: Optional[str] = None
    profile_picture_url: Optional[str] = None
    sales_research_report: Optional[str] = None
    lead_score_analysis: Optional[str] = None
    user_profile_analysis: Optional[str] = None
    website_analysis: Optional[str] = None
    
    # Modular Nodules
    viability_analysis: Optional[str] = None
    target_pain_points: Optional[str] = None
    strategic_solutions: Optional[str] = None
    personalized_outreach: Optional[str] = None
    
    # LinkedIn Subgraph Data
    post_engagements: Optional[str] = None # JSON string
    company_news: Optional[str] = None     # JSON string
    hiring_data: Optional[str] = None      # JSON string

    lead_score: Optional[int] = None
    project_urgency: Optional[int] = None
    email_history: Optional[str] = None  # JSON string
    intent_analysis: Optional[str] = None  # JSON string


class ResearchReportCreate(ResearchReportBase):
    pass

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

class IntegrationSettings(BaseModel):
    tavily_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    user_linkedin_url: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    email_config: Optional[str] = None


class OrganizationSettingsBase(BaseModel):
    icp_json: Optional[str] = None
    tavily_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    user_linkedin_url: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    email_config: Optional[str] = None

    crm_config: Optional[str] = None

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

class CompetitorCreate(CompetitorBase):
    pass

class Competitor(CompetitorBase):
    id: UUID
    created_at: datetime

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
    
    comment_history: Optional[str] = None
    source_posts: Optional[str] = None
    interaction_history: Optional[str] = None
    profile_metadata: Optional[str] = None

class IdentifiedProfileCreate(IdentifiedProfileBase):
    pass

class IdentifiedProfile(IdentifiedProfileBase):
    id: UUID
    created_at: datetime
    last_interaction_at: Optional[datetime] = None
    latest_report_id: Optional[UUID] = None  # New field for linking

    class Config:
        from_attributes = True
