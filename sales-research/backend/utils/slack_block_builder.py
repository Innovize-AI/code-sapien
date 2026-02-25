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
    title: str = None
) -> List[Dict[str, Any]]:
    """
    Builds a Slack Block Kit message for a Potential Lead discovery.
    """
    if not title:
        status_emoji = "🔥" if intent == "interested" else "🚨" if intent == "pain_point" else "👀"
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
                "text": f"*{name}* ({headline or 'No headline'})\n<{linkedin_url}|View LinkedIn Profile>"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Intent:* {intent.capitalize()}"},
                {"type": "mrkdwn", "text": f"*Sentiment:* {sentiment.capitalize()}"},
                {"type": "mrkdwn", "text": f"*Competitor:* {competitor or 'Unknown'}"},
                {"type": "mrkdwn", "text": f"*Source:* {source}"}
            ]
        }
    ]

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
    pain_points: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Builds a Slack Block Kit message when a deep research analysis is finished.
    """
    score_emoji = "💎" if lead_score >= 80 else "⭐️" if lead_score >= 60 else "📊"
    
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
                {"type": "mrkdwn", "text": f"*Heat Rating:* `{'🔥' * (max(1, heat_rating // 20) if heat_rating else 1)}` ({heat_rating or 'N/A'}/100)" if heat_rating else "*Heat Rating:* N/A"}
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
