from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ResearchReportBase(BaseModel):
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    fullname: Optional[str] = None
    profile_picture_url: Optional[str] = None
    sales_research_report: Optional[str] = None
    lead_score_analysis: Optional[str] = None
    user_profile_analysis: Optional[str] = None
    website_analysis: Optional[str] = None
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
    email_config: Optional[str] = None

class OrganizationSettingsBase(BaseModel):
    icp_json: Optional[str] = None
    tavily_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
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
