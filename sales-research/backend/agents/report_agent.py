from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
import json

from prompts.sales_prompts import REPORT_GENERATOR_PROMPT
from models.openai_models import get_open_ai
from models.structured_output import GlobalExecutiveBriefing

def sales_research_report_generator(state: AgentState):
    user_profile_analysis_dict = state.get('user_profile_analysis', {})
    user_profile_analysis = ""
    if isinstance(user_profile_analysis_dict, dict) and user_profile_analysis_dict:
        user_profile_analysis = f"""
        - Profile Summary: {user_profile_analysis_dict.get('profile_summary')}
        - Strategic Fit: {user_profile_analysis_dict.get('strategic_role_fit')}
        - Company Signals: {user_profile_analysis_dict.get('company_signals')}
        - Pain Point Hypothesis: {user_profile_analysis_dict.get('pain_point_hypothesis')}
        """
        posts = user_profile_analysis_dict.get('posts_analysis', [])
        if posts:
            user_profile_analysis += "\n        - Recent Posts:\n"
            for p in posts:
                user_profile_analysis += f"          * {p.get('post_title')} ({p.get('posted_date')}): {p.get('summary')} [Link: {p.get('post_url')}]\n"
    else:
        user_profile_analysis = str(user_profile_analysis_dict)

    website_analysis_dict = state.get("website_analysis", {})
    website_analysis = ""
    if isinstance(website_analysis_dict, dict) and website_analysis_dict:
        website_analysis = f"""
        - Industry: {website_analysis_dict.get('industry')}
        - Summary: {website_analysis_dict.get('summary')}
        - Target Audience: {website_analysis_dict.get('target_audience')}
        - Offers: {", ".join(website_analysis_dict.get('core_offerings', []))}
        - Pain Points: {", ".join(website_analysis_dict.get('industry_pain_points', []))}
        - Competitive Advantage: {website_analysis_dict.get('competitive_advantage')}
        """
    else:
        website_analysis = str(website_analysis_dict)

    company_context = state.get("company_context", "")
    lead_score_dict = state.get("lead_score_analysis", {})
    
    # Format structured lead score analysis
    lead_score_analysis = ""
    if isinstance(lead_score_dict, dict) and lead_score_dict:
        breakdown = lead_score_dict.get('score_breakdown', {})
        breakdown_lines = []
        for cat, data in breakdown.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                reason = data.get('reasoning', 'N/A')
                breakdown_lines.append(f"          * {cat.replace('_', ' ').title()}: {score} - {reason}")
        
        breakdown_str = "\n".join(breakdown_lines)
        recommendations = "\n".join([f"      * {r}" for r in lead_score_dict.get('recommendations', [])])
        
        lead_score_analysis = f"""
        - Total Score: {lead_score_dict.get('total_score')}
        - Detailed Breakdown:
{breakdown_str}
        - Analysis: {lead_score_dict.get('analysis')}
        - Recommendations:
{recommendations}
        """
    else:
        lead_score_analysis = str(lead_score_dict)
    
    # New Modular Content
    pain_points = state.get("target_pain_points", "")
    solutions = state.get("strategic_solutions", "")
    outreach = state.get("personalized_outreach", "")
    
    # Strategy Section (Outreach vs Follow-up)
    outreach_data = state.get("personalized_outreach", "")
    follow_up = state.get("follow_up_strategy", "")
    
    outreach_str = ""
    if isinstance(outreach_data, dict) and outreach_data:
        outreach_str = f"""
        Hook: {outreach_data.get('hook')}
        LinkedIn: {outreach_data.get('linkedin_message')}
        Email Subject: {outreach_data.get('email_subject')}
        Email Body: {outreach_data.get('email_body')}
        """
    else:
        outreach_str = str(outreach_data)

    strategy_output = ""
    if follow_up:
        strategy_output = f"- High-Impact Follow-up Strategy: {follow_up}"
    else:
        strategy_output = f"- Outreach Strategy Design: {outreach_str}"

    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    company_industries = state.get("company_industries", [])
    company_stats = state.get("company_stats", {})
    
    # Strategic Recommendations
    recommender_dict = state.get("buyer_journey_analysis", {})
    strategic_recommendations = ""
    if isinstance(recommender_dict, dict) and recommender_dict:
        strategic_recommendations = f"""
        - Journey Stage: {recommender_dict.get('journey_stage')}
        - Optimal Play: {recommender_dict.get('optimal_play')}
        - Strategic Reasoning: {recommender_dict.get('strategic_reasoning')}
        - Sentiment/Heat Score: {recommender_dict.get('sentiment_score')}/100
        - Urgency: {recommender_dict.get('urgency_level')}
        """
    else:
        strategic_recommendations = str(recommender_dict)

    input_content = f"""
    1. COMPANY INTELLIGENCE:
    - Name: {company_name}
    - Description: {company_description}
    - Industries: {", ".join(company_industries) if isinstance(company_industries, list) else company_industries}
    - Stats: {json.dumps(company_stats) if company_stats else "N/A"}

    2. PERSONA ANALYSIS SUMMARY:
    {user_profile_analysis}
    
    3. WEBSITE & COMPANY POSITIONING:
    {website_analysis}
    
    4. QUALIFICATION DATA & INTENT:
    {lead_score_analysis}
    
    5. STRATEGIC EVALUATIONS & ADVISORY:
    - Discovered Pain Points: {pain_points}
    - Proposed Strategic Solutions: {solutions}
    {strategy_output}
    - Strategic Recommendations: {strategic_recommendations}
    """
    
    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT.format(
            content=input_content,
            company_context=company_context
        )),
        HumanMessage(content=f"Synthesize the research for this prospect.")
    ]

    llm = get_open_ai(model="gpt-4o", temperature=0.7) # GPT-4o for strategic synthesis
    structured_llm = llm.with_structured_output(GlobalExecutiveBriefing)
    response = structured_llm.invoke(messages)

    return {"sales_research_report": response.model_dump()}


