import json
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
    user_id: str = None
):
    """
    Logs an activity to the database and sends a Slack notification if configured.
    """
    # 1. Create activity in DB
    metadata_json = json.dumps(metadata) if metadata else None
    
    # Extract intent/sentiment from metadata if available
    intent = metadata.get("intent") if metadata else None
    sentiment = metadata.get("sentiment") if metadata else None

    await create_activity(
        db, 
        type=type, 
        title=title, 
        description=description, 
        metadata_json=metadata_json,
        intent=intent,
        sentiment=sentiment,
        user_id=user_id
    )

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
    settings = await get_org_settings(db)
    if settings and settings.slack_webhook_url:
        blocks = None
        
        # Build specific blocks based on type/metadata
        if type == "high_potential" or (metadata and metadata.get("is_fit")) or (type == "comment" and metadata and metadata.get("linkedin_url")):
            # Determine source text
            source_text = "Competitor Comment"
            competitor_val = metadata.get("competitor", "")
            if competitor_val and competitor_val.startswith("Keyword:"):
                 source_text = competitor_val

            blocks = build_hot_lead_blocks(
                name=metadata.get("name", "Unknown"),
                headline=metadata.get("headline", ""),
                linkedin_url=metadata.get("linkedin_url", ""),
                comment=metadata.get("comment", ""),
                competitor=metadata.get("competitor", ""),
                intent=intent or "curious",
                sentiment=sentiment or "neutral",
                reasoning=metadata.get("fit_reasoning", ""),
                source=source_text,
                post_link=metadata.get("source_post_url"),
                rep_name=rep_name,
                title=title
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
                pain_points=metadata.get("pain_points")
            )
        else:
            blocks = build_generic_activity_blocks(title, description, rep_name=rep_name)

        # 3. Send Slack Notification
        if settings.slack_webhook_url:
            print(f"DEBUG: Sending Slack notification for {title}. Blocks: {len(blocks) if blocks else 0}")
            if blocks:
                print(f"DEBUG: Payload: {json.dumps(blocks, indent=2)[:1000]}") # Log first 1000 chars of blocks
            
            slack_text = f"*{title}*\n{description}" if description else f"*{title}*"
            await send_slack_notification(settings.slack_webhook_url, slack_text, blocks=blocks)
