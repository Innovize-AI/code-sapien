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
    email: str = None,
    email_verification_status: str = None,
    post_topic_depth: str = None,
    is_decision_maker: bool = False,
    discovery_source: str = "other",
    signal_reason: str = None,
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
                "text": (
                    f"*{name}* ({headline or 'No headline'})"
                    + (
                        "\n📧 " + email + " " + {
                            "ok": "✅ _verified_",
                            "catch_all": "⚠️ _catch-all_",
                            "invalid": "❌ _invalid_",
                            "error": "❓ _unknown_",
                            "unknown": "❓ _unknown_",
                        }.get(email_verification_status or "", "")
                        if email else ""
                    )
                    + f"\n<{linkedin_url}|View LinkedIn Profile>"
                )
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

    is_keyword = discovery_source == "keyword"
    competitor_clean = (competitor or "").replace("Keyword:", "").strip()

    fields = [
        {"type": "mrkdwn", "text": f"*Intent:* {intent.replace('_', ' ').title()}"},
        {"type": "mrkdwn", "text": f"*Sentiment:* {sentiment.capitalize()}"},
    ]

    if is_keyword:
        fields.append({"type": "mrkdwn", "text": f"*Keyword:* {competitor_clean}"})
        if post_topic_depth and post_topic_depth != "generic_engagement":
            fields.append({"type": "mrkdwn", "text": f"*Topic Depth:* {post_topic_depth.replace('_', ' ').title()}"})
    elif competitor and competitor not in ("Apollo", "LinkedIn Jobs"):
        fields.append({"type": "mrkdwn", "text": f"*Competitor:* {competitor}"})
    elif competitor in ("Apollo", "LinkedIn Jobs"):
        fields.append({"type": "mrkdwn", "text": f"*Discovered via:* {competitor}"})

    if is_decision_maker:
        fields.append({"type": "mrkdwn", "text": "*Role Level:* Decision Maker 🎯"})

    blocks.append({
        "type": "section",
        "fields": fields
    })

    if signal_reason:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"💡 *Why this lead:* {signal_reason}"}]
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

def build_lead_digest_blocks(
    leads: list,
    rep_name: str = None,
    source_label: str = None,
) -> List[Dict[str, Any]]:
    """
    Builds a single grouped Slack digest for a batch of qualified leads.
    Each lead dict: tier ("hot"|"hand_raiser"|"pain_point"|"qualified"),
    name, linkedin_url, headline, email, email_verification_status,
    company_name, employee_count, company_industries, intent, sentiment,
    competitor, signal_reason, post_link, comment, reasoning, is_buy_signal,
    post_topic_depth.
    """
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%a, %b ") + str(now.day)

    hot         = [l for l in leads if l.get("tier") == "hot"]
    hand_raisers = [l for l in leads if l.get("tier") == "hand_raiser"]
    pain_points  = [l for l in leads if l.get("tier") == "pain_point"]
    qualified    = [l for l in leads if l.get("tier") == "qualified"]

    summary_parts = []
    if hot:          summary_parts.append(f"🔥 {len(hot)} hot")
    if hand_raisers: summary_parts.append(f"🙋 {len(hand_raisers)} hand raiser{'s' if len(hand_raisers) > 1 else ''}")
    if pain_points:  summary_parts.append(f"🚨 {len(pain_points)} pain point{'s' if len(pain_points) > 1 else ''}")
    if qualified:    summary_parts.append(f"👀 {len(qualified)} qualified")
    meta_text = "  ·  ".join(summary_parts)
    if rep_name:
        meta_text += f"  |  Assigned to: {rep_name}"

    header_text = "📋 Lead Intelligence Digest"
    if source_label:
        header_text += f" — {source_label}"
    header_text += f" — {date_str}"

    blocks: List[Dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": header_text, "emoji": True}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": meta_text}]},
        {"type": "divider"},
    ]

    email_badges = {"ok": "✅", "catch_all": "⚠️", "invalid": "❌", "error": "❓", "unknown": "❓"}

    def add_tier(tier_leads: list, tier_emoji: str, tier_label: str):
        if not tier_leads:
            return
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{tier_emoji} *{tier_label}* ({len(tier_leads)})"}
        })
        for lead in tier_leads:
            name             = lead.get("name") or "Unknown"
            headline         = lead.get("headline") or ""
            url              = lead.get("linkedin_url") or ""
            email            = lead.get("email")
            email_status     = lead.get("email_verification_status")
            company_name     = lead.get("company_name")
            employee_count   = lead.get("employee_count")
            company_industries = lead.get("company_industries") or []
            intent           = lead.get("intent") or ""
            sentiment        = lead.get("sentiment") or ""
            competitor       = lead.get("competitor") or ""
            signal_reason    = lead.get("signal_reason") or ""
            post_link        = lead.get("post_link")
            comment          = lead.get("comment") or ""
            reasoning        = lead.get("reasoning") or ""
            is_buy_signal    = lead.get("is_buy_signal", False)
            post_topic_depth = lead.get("post_topic_depth") or ""

            is_keyword = str(competitor).startswith("Keyword:")
            competitor_clean = competitor.replace("Keyword:", "").strip()

            # ── Line 1: name + headline ─────────────────────────────────
            line1 = f"*{name}*"
            if headline:
                truncated = headline[:85] + ("..." if len(headline) > 85 else "")
                line1 += f"  |  _{truncated}_"

            lines = [line1]

            # ── Email badge ─────────────────────────────────────────────
            if email:
                badge = email_badges.get(email_status or "", "")
                lines.append(f"📧 {email} {badge}".strip())

            # ── Company + meta row ──────────────────────────────────────
            detail_parts = []
            if company_name:
                co = f"🏢 {company_name}"
                if employee_count:
                    co += f" ({employee_count} emp)"
                if company_industries:
                    co += f"  ·  {', '.join(company_industries[:2])}"
                detail_parts.append(co)
            if intent:
                intent_label = intent.replace("_", " ").title()
                if is_buy_signal:
                    intent_label = f"⚡ {intent_label} (Buy Signal)"
                detail_parts.append(intent_label)
            if sentiment:
                detail_parts.append(f"Sentiment: {sentiment.capitalize()}")
            if is_keyword and competitor_clean:
                detail_parts.append(f"Keyword: _{competitor_clean}_")
            elif competitor and competitor not in ("Apollo", "LinkedIn Jobs"):
                detail_parts.append(f"via {competitor}")
            elif competitor in ("Apollo", "LinkedIn Jobs"):
                detail_parts.append(f"via {competitor}")
            if post_topic_depth and post_topic_depth != "generic_engagement":
                detail_parts.append(f"Depth: {post_topic_depth.replace('_', ' ').title()}")
            if detail_parts:
                lines.append("  ·  ".join(detail_parts))

            if signal_reason:
                lines.append(f"💡 *Why this lead:* {signal_reason}")

            lines.append(f"<{url}|View LinkedIn Profile>" if url else "No LinkedIn URL")

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)}
            })

            # ── Context block: comment snippet + AI reasoning ───────────
            context_elements = []
            if comment:
                snippet = comment[:200].replace("\n", " ") + ("..." if len(comment) > 200 else "")
                context_elements.append({"type": "mrkdwn", "text": f"💬 _{snippet}_"})
            if reasoning:
                r_clean = reasoning.replace("\n", " ")
                context_elements.append({"type": "mrkdwn", "text": f"🤖 *AI:* {r_clean}"})
            if context_elements:
                blocks.append({"type": "context", "elements": context_elements})

            # ── Action buttons ──────────────────────────────────────────
            action_elements = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Analyze Lead"},
                    "style": "primary",
                    "action_id": "analyze_lead",
                    "value": url or "unknown",
                }
            ]
            if post_link:
                action_elements.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Post"},
                    "url": post_link,
                })
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Ignore"},
                "action_id": "ignore_lead",
                "value": url or "unknown",
            })
            blocks.append({"type": "actions", "elements": action_elements})

        blocks.append({"type": "divider"})

    add_tier(hot,          "🔥", "HOT LEADS")
    add_tier(hand_raisers, "🙋", "HAND RAISERS")
    add_tier(pain_points,  "🚨", "PAIN POINTS")
    add_tier(qualified,    "👀", "QUALIFIED LEADS")

    # Slack enforces a 50-block limit per message
    return blocks[:50]


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
