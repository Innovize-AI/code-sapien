import os
from typing import List, Dict, Any

def build_hot_lead_blocks(
    name: str, 
    headline: str, 
    linkedin_url: str, 
    comment: str, 
    competitor: str, 
    intent: str, 
    sentiment: str,
    reasoning: str,
    source: str = "Competitor Comment",
    post_link: str = None,
    rep_name: str = None,
    title: str = None,
    company_name: str = None,
    company_description: str = None,
    company_industries: List[str] = None,
    employee_count: int = None,
    revenue: str = None,
    is_buy_signal: bool = False,
    is_strategic_seller: bool = False,
    email: str = None
) -> List[Dict[str, Any]]:

    """
    Builds a Slack Block Kit message for a Potential Lead discovery.
    """
    if not title:
        # Define emojis for new intent mapping
        emoji_map = {
            "hand_raiser": "🔥",
            "prospect_pain": "🚨",
            "passive_expert": "🧠",
            "strategic_seller": "🗣️",
            "low_signal": "👀"
        }
        status_emoji = emoji_map.get(intent, "👀")
        
        # Override emoji if explicit signals are present
        if is_buy_signal:
            status_emoji = "⚡"
        elif is_strategic_seller:
            status_emoji = "🗣️"
            
        title = f"{status_emoji} *Potential Opportunity: {name}*"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title.replace("*", ""), # Strip markdown for header
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}* ({headline or 'No headline'})" + (f"\n📧 {email}" if email else "") + f"\n<{linkedin_url}|View LinkedIn Profile>"
            }
        }
    ]

    # Add Signals / Badges
    signal_elements = []
    if is_buy_signal:
        signal_elements.append({"type": "mrkdwn", "text": "⚡ *BUY SIGNAL* (High Intent)"})
    if is_strategic_seller:
        signal_elements.append({"type": "mrkdwn", "text": "🗣️ *STRATEGIC SELLER* (Low Priority)"})
    
    if signal_elements:
        blocks.append({
            "type": "context",
            "elements": signal_elements
        })

    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Intent:* {intent.capitalize()}"},
            {"type": "mrkdwn", "text": f"*Sentiment:* {sentiment.capitalize()}"},
            {"type": "mrkdwn", "text": f"*Competitor:* {competitor or 'Unknown'}"},
            {"type": "mrkdwn", "text": f"*Source:* {source}"}
        ]
    })

    # Add Company Info
    if company_name:
        company_text = f"🏢 *Company:* {company_name}"
        if company_industries:
            company_text += f" ({', '.join(company_industries[:2])})"
        
        company_details = []
        if employee_count:
            company_details.append(f"👥 {employee_count} employees")
        if revenue:
            company_details.append(f"💰 {revenue} revenue")
        
        if company_details:
            company_text += f"\n_{' • '.join(company_details)}_"
            
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": company_text
            }
        })
        
        if company_description:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*About:* {company_description[:200]}..." if len(company_description) > 200 else f"*About:* {company_description}"}
                ]
            })


    if rep_name:
        blocks.insert(1, {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"👤 *Assigned Rep:* {rep_name}"}
            ]
        })

    if comment:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Comment/Post Content:* _{comment}_"
            }
        })

    if reasoning:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Reasoning:* {reasoning}"
            }
        })

    actions_elements = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Analyze Lead & Draft Plan"},
            "style": "primary",
            "action_id": "analyze_lead",
            "value": linkedin_url
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Ignore"},
            "action_id": "ignore_lead",
            "value": linkedin_url
        }
    ]

    if post_link:
        actions_elements.insert(1, {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Post"},
            "url": post_link
        })

    blocks.append({
        "type": "actions",
        "elements": actions_elements
    })

    return blocks

def build_generic_activity_blocks(title: str, description: str, metadata: dict = None, rep_name: str = None) -> List[Dict[str, Any]]:
    """
    Fallback for generic activities.
    """
    blocks = []
    if rep_name:
         blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"👤 *Activity by:* {rep_name}"}
            ]
        })

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{title}*\n{description or ''}"
        }
    })
    return blocks

def build_research_completed_blocks(
    name: str, 
    lead_score: int, 
    why_now: str, 
    action_plan: List[str], 
    report_id: str,
    rep_name: str = None,
    journey_stage: str = None,
    heat_rating: int = None,
    urgency: str = None,
    pain_points: List[str] = None,
    company_name: str = None,
    company_description: str = None,
    company_industries: List[str] = None,
    employee_count: int = None,
    revenue: str = None
) -> List[Dict[str, Any]]:

    """
    Builds a Slack Block Kit message when a deep research analysis is finished.
    """
    score_emoji = "💎" if lead_score >= 80 else "⭐️" if lead_score >= 60 else "📊"
    
    # Defensive cast for heat_rating
    try:
        heat_rating_int = int(heat_rating) if heat_rating is not None and str(heat_rating).isdigit() else 0
    except:
        heat_rating_int = 0

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"✅ Research Complete: {name}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Lead Score:* {score_emoji} `{lead_score}/100`"},
                {"type": "mrkdwn", "text": f"*Heat Rating:* `{'🔥' * (max(1, heat_rating_int // 20) if heat_rating_int else 1)}` ({heat_rating_int}/100)" if heat_rating_int else "*Heat Rating:* `N/A`"}
            ]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Journey Stage:* `{journey_stage or 'Awareness'}`"},
                {"type": "mrkdwn", "text": f"*Urgency:* `{urgency or 'Medium'}`"}
            ]
        }
    ]

    # Add Company Data
    if company_name:
        stats_line = ""
        if employee_count:
            stats_line += f"👥 {employee_count} employees  "
        if revenue:
            stats_line += f"💰 {revenue} revenue"
            
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🏢 *{company_name}*\n{stats_line}"
            }
        })
        
        if company_industries:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📍 *Industries:* {', '.join(company_industries)}"}
                ]
            })

        if company_description:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Company Overview:*\n{company_description[:300]}..." if len(company_description) > 300 else f"*Company Overview:*\n{company_description}"
                }
            })


    if rep_name:
        blocks.insert(1, {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"👤 *Researched by:* {rep_name}"}
            ]
        })

    if why_now:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Why Now?*\n{why_now}"
            }
        })

    if pain_points:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Primary Pain Points:*\n" + "\n".join([f"• {pp}" for pp in pain_points[:3]])
            }
        })

    if action_plan:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Action Plan:*\n" + "\n".join([f"• {step}" for step in action_plan[:3]])
            }
        })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Full Report"},
                "url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reports?id={report_id}", 
                "style": "primary"
            }
        ]
    })
    return blocks
