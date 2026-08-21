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
    logical_gap_mapping: str = Field(description="The 'Silent Friction' or hidden cost this solution bridges.")
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

class LinkedInPostAnalysis(BaseModel):
    post_title: str = Field(description="Title or main hook of the post")
    summary: str = Field(description="Brief summary of the post content")
    posted_date: str = Field(description="Approximate date or relative time of posting")
    post_url: str = Field(description="URL of the specific post")

class LinkedInAnalysis(BaseModel):
    profile_summary: str = Field(default="", description="Comprehensive summary of the candidate's professional profile.")
    posts_analysis: List[LinkedInPostAnalysis] = Field(default_factory=list, description="Analysis of recent posts.")
    strategic_role_fit: Optional[str] = Field(default=None, description="Assessment of role fit and decision-making power.")
    company_signals: Optional[str] = Field(default=None, description="Insights derived from company stats, hiring, and news.")
    engagement_persona: Optional[str] = Field(default=None, description="Analysis of topics they care about and communication style.")
    pain_point_hypothesis: Optional[str] = Field(default=None, description="Hypothesized pain points based on company and role context.")

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

class StrategicPlaybook(BaseModel):
    outreach_tactics: str = Field(default="", description="Cleanly presented finalized outreach tactics (LinkedIn/Email).")
    refined_hook: str = Field(default="", description="Refined Hook to connect to the journey stage.")
    strategic_proof_points: List[str] = Field(default_factory=list, description="Specific snippets/insights from playbooks used for validation.")

class GlobalExecutiveBriefing(BaseModel):
    fit_assessment: str = Field(default="[NEEDS REVIEW]", description="The 'Non-Fit' Protocol status (e.g., '[STOP: POOR FIT]' or 'GOOD FIT').")
    fit_reasoning: str = Field(default="", description="One sentence explanation for the fit assessment.")
    executive_synthesis: str = Field(default="", description="Narrative connecting the person's role/activity to company position and Innovize AI value.")
    why_now: str = Field(default="", description="2-3 sentence argument for why this specific week is the perfect time to reach out.")
    strategic_playbook: StrategicPlaybook = Field(default_factory=StrategicPlaybook, description="Finalized outreach tactics and refined hook.")
    internal_advisory: List[str] = Field(default_factory=list, description="2 'Insider Tips' for the rep.")
    advanced_strategic_pivots: List[str] = Field(
        default_factory=list, 
        description="High-impact 'If/Then' tactical advice for when the prospect engages (e.g., 'If they reply about X, offer Y')."
    )
