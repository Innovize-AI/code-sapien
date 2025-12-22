from sqlalchemy import Column, Integer, String, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
import datetime
from db.database import Base

class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    # Input Data
    linkedin_url = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    fullname = Column(Text, nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    
    # Analysis Results (Markdown Content)
    sales_research_report = Column(Text, nullable=True)
    lead_score_analysis = Column(Text, nullable=True)
    user_profile_analysis = Column(Text, nullable=True)
    website_analysis = Column(Text, nullable=True)
    
    # Metrics
    lead_score = Column(Integer, nullable=True)
    project_urgency = Column(Integer, nullable=True)
