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
    post_link: str = None
) -> List[Dict[str, Any]]:
    """
    Builds a Slack Block Kit message for a Hot Lead discovery.
    """
    status_emoji = "🔥" if intent == "interested" else "🚨" if intent == "pain_point" else "👀"
    title_text = f"{status_emoji} *Hot Lead Discovery: {name}*"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"New Potential Opportunity Found!",
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

def build_generic_activity_blocks(title: str, description: str, metadata: dict = None) -> List[Dict[str, Any]]:
    """
    Fallback for generic activities.
    """
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n{description or ''}"
            }
        }
    ]
    return blocks

def build_research_completed_blocks(
    name: str, 
    lead_score: int, 
    why_now: str, 
    action_plan: List[str], 
    report_id: str
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
            "text": {
                "type": "mrkdwn",
                "text": f"*Lead Score:* {score_emoji} `{lead_score}/100`"
            }
        }
    ]

    if why_now:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Why Now?*\n{why_now}"
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
                "url": f"http://localhost:3000/reports?id={report_id}", 
                "style": "primary"
            }
        ]
    })
    return blocks
