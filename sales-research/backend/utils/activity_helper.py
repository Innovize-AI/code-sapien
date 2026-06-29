import json
import logging

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import create_activity, get_org_settings
from utils.slack import send_slack_notification
from utils.slack_block_builder import build_hot_lead_blocks, build_generic_activity_blocks, build_research_completed_blocks

async def log_activity_and_notify(
    db: AsyncSession,
    type: str,
    title: str,
    description: str = None,
    metadata: dict = None,
    user_id: str = None,
    org_id: str = None,
    idempotency_key: str = None,
    send_slack: bool = True,
):
    """
    Logs an activity to the database and sends a Slack notification if configured.
    """
    # 1. Create activity in DB
    metadata_json = json.dumps(metadata) if metadata else None
    
    # Extract intent/sentiment from metadata if available
    intent = metadata.get("intent") if metadata else None
    sentiment = metadata.get("sentiment") if metadata else None

    activity = await create_activity(
        db, 
        type=type, 
        title=title, 
        description=description, 
        metadata_json=metadata_json,
        intent=intent,
        sentiment=sentiment,
        user_id=user_id,
        org_id=org_id,
        idempotency_key=idempotency_key
    )

    if idempotency_key and not activity:
        logger.info(f"DEBUG: Idempotency conflict for key {idempotency_key}. Skipping Slack notification.")
        # Make sure to close any implicit open transaction before returning
        await db.commit()
        return

    # 1.5 Resolve Rep Name
    rep_name = None
    if user_id:
        from db.models import Profile
        from sqlalchemy import select
        result = await db.execute(select(Profile).where(Profile.id == user_id))
        profile = result.scalars().first()
        if profile:
            rep_name = profile.email.split("@")[0].replace(".", " ").title()
    
    # 2. Fetch Slack webhook and notify
    webhook_url = None
    
    # Try fetching OrganizationSettings for the webhook
    settings = await get_org_settings(db, user_id=user_id, org_id=org_id)
    if settings and settings.slack_webhook_url:
        slack_enabled = True
        if settings.integrations_config:
            try:
                config_json = json.loads(settings.integrations_config)
                if config_json.get("slack") and not config_json["slack"].get("enabled", True):
                    slack_enabled = False
            except Exception:
                pass
                
        if slack_enabled:
            webhook_url = settings.slack_webhook_url
            logger.info(f"DEBUG: Using settings owned by {user_id or 'System'}")
        else:
            logger.info("DEBUG: Slack notification skipped because it is disabled in integrations config.")

    if webhook_url and not send_slack:
        logger.info(f"DEBUG: Slack suppressed (send_slack=False) for '{title}' — will be included in digest.")
        await db.commit()
        return

    if webhook_url:
        blocks = None

        # Build specific blocks based on type/metadata
        if type == "high_potential" or (metadata and metadata.get("is_fit")) or (type == "comment" and metadata and metadata.get("linkedin_url")):
            competitor_val = metadata.get("competitor", "") or ""
            discovery_source = metadata.get("discovery_source") or ("keyword" if str(competitor_val).startswith("Keyword:") else "other")

            blocks = build_hot_lead_blocks(
                name=metadata.get("name", "Unknown"),
                headline=metadata.get("headline", ""),
                linkedin_url=metadata.get("linkedin_url", ""),
                comment=metadata.get("comment", ""),
                competitor=competitor_val,
                intent=intent or "curious",
                sentiment=sentiment or "neutral",
                reasoning=metadata.get("fit_reasoning", ""),
                post_link=metadata.get("source_post_url"),
                rep_name=rep_name,
                title=title,
                company_name=metadata.get("company_name"),
                company_description=metadata.get("company_description"),
                company_industries=metadata.get("company_industries"),
                employee_count=metadata.get("employee_count"),
                revenue=metadata.get("revenue"),
                is_buy_signal=metadata.get("is_buy_signal", False),
                is_strategic_seller=metadata.get("is_strategic_seller", False),
                email=metadata.get("email"),
                email_verification_status=metadata.get("email_verification_status"),
                post_topic_depth=metadata.get("post_topic_depth"),
                is_decision_maker=metadata.get("is_decision_maker", False),
                discovery_source=discovery_source,
                signal_reason=metadata.get("signal_reason"),
            )
        elif type == "analysis" and metadata and metadata.get("report_id"):
            blocks = build_research_completed_blocks(
                name=metadata.get("name", "Unknown"),
                lead_score=metadata.get("lead_score", 0),
                why_now=metadata.get("why_now", ""),
                action_plan=metadata.get("action_plan", []),
                report_id=metadata.get("report_id"),
                rep_name=rep_name,
                journey_stage=metadata.get("journey_stage"),
                heat_rating=metadata.get("heat_rating"),
                urgency=metadata.get("urgency"),
                pain_points=metadata.get("pain_points"),
                company_name=metadata.get("company_name"),
                company_description=metadata.get("company_description"),
                company_industries=metadata.get("company_industries"),
                employee_count=metadata.get("employee_count"),
                revenue=metadata.get("revenue")
            )

        else:
            blocks = build_generic_activity_blocks(title, description, rep_name=rep_name)

        # 3. Send Slack Notification
        if webhook_url:
            logger.info(f"DEBUG: Sending Slack notification for {title}. Blocks: {len(blocks) if blocks else 0}")
            if blocks:
                logger.info(f"DEBUG: Payload: {json.dumps(blocks, indent=2)[:1000]}") # Log first 1000 chars of blocks
            
            slack_text = f"*{title}*\n{description}" if description else f"*{title}*"
            await send_slack_notification(webhook_url, slack_text, blocks=blocks)

    # SECURE THE TRANSACTION: Clean up any implicitly opened read-transactions
    # (like from selecting the Profile or UserSettings) to ensure the session 
    # doesn't leak open locks back to the caller's orchestrator loops.
    await db.commit()
