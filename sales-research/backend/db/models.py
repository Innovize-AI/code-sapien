from sqlalchemy import Column, Integer, String, Text, DateTime, text, Boolean
from sqlalchemy.dialects.postgresql import UUID
import datetime
from db.database import Base

class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    # Input Data
    linkedin_url = Column(Text, nullable=True)
    email_id = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    fullname = Column(Text, nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    company_name = Column(Text, nullable=True)
    company_description = Column(Text, nullable=True)
    company_industries = Column(Text, nullable=True) # JSON array
    company_stats = Column(Text, nullable=True)      # JSON object

    
    # Analysis Results (Markdown Content)
    sales_research_report = Column(Text, nullable=True)
    lead_score_analysis = Column(Text, nullable=True)
    user_profile_analysis = Column(Text, nullable=True)
    website_analysis = Column(Text, nullable=True)
    cso_strategic_briefing = Column(Text, nullable=True)
    
    # Modular Nodules
    viability_analysis = Column(Text, nullable=True)
    target_pain_points = Column(Text, nullable=True)
    strategic_solutions = Column(Text, nullable=True)
    personalized_outreach = Column(Text, nullable=True)
    follow_up_strategy = Column(Text, nullable=True)
    buyer_journey_analysis = Column(Text, nullable=True) # JSON object
    meeting_notes = Column(Text, nullable=True)
    
    # LinkedIn Subgraph Data
    post_engagements = Column(Text, nullable=True) # JSON array
    company_news = Column(Text, nullable=True)     # JSON array
    hiring_data = Column(Text, nullable=True)      # JSON array
    company_stats = Column(Text, nullable=True)    # JSON object
    lead_company_linkedin_url = Column(Text, nullable=True)
    lead_li_urn = Column(Text, nullable=True)
    
    # Metrics
    lead_score = Column(Integer, nullable=True)
    project_urgency = Column(Integer, nullable=True)
    
    # New Email & Intent Analysis
    email_history = Column(Text, nullable=True)  # JSON array of email objects
    intent_analysis = Column(Text, nullable=True)  # JSON object with intent data
    extra_metadata = Column(Text, nullable=True)   # JSON object for extra fields from webhooks/forms

class LeadSubmission(Base):
    __tablename__ = "lead_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    email = Column(String, nullable=False)
    linkedin_url = Column(String, nullable=True)
    source = Column(String, nullable=False) # 'webhook', 'form', 'calendly', 'cal'
    
    payload = Column(Text, nullable=True) # Full JSON payload
    
    # Action-based system
    action_type = Column(String, nullable=True, server_default=text("'form_submission'")) # e.g., 'booked_call', 'downloaded_magnet', 'form_submission'
    action_metadata = Column(Text, nullable=True) # JSON store for action-specific data (call time, magnet name, etc.)
    
    # Specific form tracking
    external_form_id = Column(String, nullable=True)
    external_form_name = Column(String, nullable=True)
    
    # Link to resulting report if processed
    research_id = Column(UUID(as_uuid=True), nullable=True)
    # Email & Intent Analysis
    email_history = Column(Text, nullable=True)    # JSON array
    intent_analysis = Column(Text, nullable=True)  # JSON object
    extra_metadata = Column(Text, nullable=True)   # JSON object


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))
    
    # For now, we assume single tenant or global settings. 
    # In future, add user_id or org_id here.
    
    # Store ICP as JSON
    icp_json = Column(Text, nullable=True) # Storing JSON string for flexibility
    
    # Integration Keys
    tavily_api_key = Column(String, nullable=True)
    apollo_api_key = Column(String, nullable=True)

    # LinkedIn Identity for Engagement Tracking
    user_linkedin_url = Column(Text, nullable=True)
    company_linkedin_url = Column(Text, nullable=True)
    
    # New Configs

    email_config = Column(Text, nullable=True) # JSON store for IMAP details
    crm_config = Column(Text, nullable=True)   # JSON store for CRM details
    integrations_config = Column(Text, nullable=True) # JSON store for all third-party integrations
    onboarding_complete = Column(Integer, server_default=text("0"), nullable=False) # 0 or 1
    kit_api_key = Column(String, nullable=True) # Public Key for v3
    kit_api_secret = Column(String, nullable=True) # Secret Key for v3
    slack_webhook_url = Column(String, nullable=True)

class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    competitor_urls = Column(Text, nullable=False) # Store comma-separated or JSON list
    analysis_report = Column(Text, nullable=False)

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    name = Column(String, nullable=True)
    linkedin_url = Column(Text, nullable=False, unique=True)

class IdentifiedProfile(Base):
    __tablename__ = "identified_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    name = Column(String, nullable=True)
    headline = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=False, unique=True)
    
    # Classification
    is_fit = Column(Boolean, default=False)
    is_competitor = Column(Boolean, default=False)
    is_decision_maker = Column(Boolean, default=False)
    fit_reasoning = Column(Text, nullable=True)
    intent = Column(String, nullable=True) # 'interested', 'pain_point', 'curious'
    sentiment = Column(String, nullable=True) # 'positive', 'neutral', 'negative'

    # Aggregated Data
    comment_history = Column(Text, nullable=True) # JSON array of comments
    source_posts = Column(Text, nullable=True)    # JSON array of {title, url, competitor}
    interaction_history = Column(Text, nullable=True) # Hierarchical: [ { competitor, posts: [ {url, title, comments: []} ] } ]
    
    # Status/Metadata
    last_interaction_at = Column(DateTime(timezone=True), server_default=text("now()"))
    profile_metadata = Column(Text, nullable=True)         # JSON for flexibility

class Activity(Base):
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    
    type = Column(String, nullable=False) # 'meeting', 'email', 'comment', 'analysis', 'high_potential'
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True) # JSON object for extra details
    intent = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
