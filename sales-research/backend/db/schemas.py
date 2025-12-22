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

class ResearchReportCreate(ResearchReportBase):
    pass

class ResearchReport(ResearchReportBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
