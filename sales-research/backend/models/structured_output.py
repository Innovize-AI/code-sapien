from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date 
class ViabilityAssessment(BaseModel):
    demographic_fit: str = Field(description="Assessment of industry, size, and revenue fit.")
    authority: str = Field(description="Assessment of the prospect's decision-making power.")
    strategic_alignment: str = Field(description="Overall alignment with Innovize AI's target profile.")
    is_competitor: bool = Field(description="True if the prospect is a direct competitor to Innovize AI.")
    competitor_reasoning: Optional[str] = Field(description="Explanation of why they are or are not a competitor.")
    score: int = Field(description="A score from 1-10 on viability.")
    verdict: str = Field(description="A one-sentence summary (e.g., 'Highly Viable - Pursuit Recommended')")

class PainPoint(BaseModel):
    title: str = Field(description="A short, catchy title for the pain point.")
    description: str = Field(description="Detailed explanation of the challenge.")
    impact: str = Field(description="The business impact of this pain point.")

class PainPoints(BaseModel):
    points: List[PainPoint] = Field(description="List of identified pain points.")

class Solution(BaseModel):
    title: str = Field(description="Name of the proposed solution.")
    description: str = Field(description="How the solution works.")
    expected_roi: str = Field(description="Potential efficiency or revenue gains.")

class StrategicSolutions(BaseModel):
    solutions: List[Solution] = Field(description="List of tailored solutions.")

class OutreachStrategy(BaseModel):
    hook: str = Field(description="A personalized opening based on recent news or posts.")
    linkedin_message: str = Field(description="A short, high-conversion LinkedIn message.")
    email_subject: str = Field(description="A compelling email subject line.")
    email_body: str = Field(description="A hyper-personalized, value-first email.")

class LeadExtractedData(BaseModel):
    industry: str
    company_size: str
    revenue: str
    job_title: str
    website_visits: Optional[int] = 0
    visited_high_value_pages: bool = False
    content_interaction: str = "None"
    demo_request: bool = False
    form_submission: bool = False
    social_media_engagement: bool = False
    recent_activity: bool = False
    buying_stage: str = "Awareness"
    referral_partner_introduction: bool = False
    inbound_marketing: bool = False
    paid_ad_click: bool = False
    cold_outreach: bool = False
    purchase_timeline: str = "Unknown"
    project_urgency: str = "Low"

class LeadScoreResponse(BaseModel):
    demographic_fit_score: int
    engagement_score: int
    sales_readiness_score: int
    lead_source_score: int
    timing_score: int
    total_lead_score: int
    analysis: str = Field(description="Detailed breakdown of the scoring.")
    recommendations: List[str] = Field(description="Recommended next steps.")

class Post(BaseModel):
    post_summary: str =Field(description="summary of the post")
    post_date: date =Field(description= "Date of post")
    post_title: str =Field(description= "Post title")

class LinkedInAnalysis(BaseModel):
    archetype: str = Field(description="The professional persona or archetype.")
    summary: str = Field(description="A professional summary.")
    key_themes: List[str] = Field(description="Main topics and themes in their content.")
    recent_sentiment: str = Field(description="Sentiment and focus of recent activity.")
    communication_style: str = Field(description="Tone and style of their communication (e.g., 'Direct and Data-Driven').")
    professional_intelligence: str = Field(description="Deeper insights into their expertise, influence, and professional focus.")
    strategic_value: str = Field(description="Why this profile is strategically interesting for Innovize AI.")
    recent_posts: List[Post]= Field(description="List of recent posts")

class WebsiteAnalysis(BaseModel):
    mission: str = Field(description="The company's core mission and values.")
    target_audience: str = Field(description="Who the company serves.")
    offerings: List[str] = Field(description="Key products or services.")
    pain_points_solved: List[str] = Field(description="Challenges they solve for clients.")
    recent_news: Optional[str] = Field(description="Any news or highlights found")
    market_context: Optional[str] = Field(description="Wider industry or market context discovered.")
    competitive_landscape: Optional[str] = Field(description="Brief overview of how they fit against competitors.")

class SalesResearchReport(BaseModel):
    why_now: str = Field(description="Strategic reasoning for why this prospect is a priority today.")
    strategic_hook: str = Field(description="A powerful opening strategy for engagement.")
    solution_fit_summary: str = Field(description="Brief summary of why Innovize AI matches their current goals.")
    market_analysis: str = Field(description="Detailed industry and market trends relevant to this prospect.")
    competitive_positioning: str = Field(description="How the prospect stands against competitors and how we help them win.")
    action_plan: List[str] = Field(description="A 3-step actionable plan for the sales representative.")


