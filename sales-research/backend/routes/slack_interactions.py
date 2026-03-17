import json
from fastapi import APIRouter, Request, BackgroundTasks, Form, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import UserSettings
import httpx

slack_interactions_router = APIRouter(tags=['Slack Interactions'], responses={404: {"description": "Not found"}},)

@slack_interactions_router.post("/slack/interactions")
async def handle_slack_interactions(
    background_tasks: BackgroundTasks,
    payload: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Handles interactions from Slack Block Kit (buttons, etc).
    """
    try:
        print(f"DEBUG: Received Slack interaction payload: {payload[:200]}...")
        data = json.loads(payload)
        user = data.get("user", {}).get("name", "Someone")
        actions = data.get("actions", [])
        response_url = data.get("response_url")
        
        print(f"DEBUG: Parsed Slack action from {user}: {actions}")

        if not actions:
            return {"ok": True}

        action = actions[0]
        action_id = action.get("action_id")
        linkedin_url = action.get("value")

        # Resolve User ID from Slack ID
        slack_user_id = data.get("user", {}).get("id")
        internal_user_id = None
        if slack_user_id:
            try:
                result = await db.execute(select(UserSettings).where(UserSettings.slack_user_id == slack_user_id))
                user_settings = result.scalars().first()
                if user_settings:
                    internal_user_id = str(user_settings.user_id)
                    print(f"DEBUG: Resolved Slack User {slack_user_id} to Internal User {internal_user_id}")
                else:
                    print(f"DEBUG: No internal user found for Slack User {slack_user_id}")
            except Exception as e:
                print(f"Error resolving Slack user: {e}")

        if action_id == "analyze_lead" and linkedin_url:
            # 1. Respond to Slack in background (to avoid 3s timeout) IMMEDIATELY
            if response_url:
                background_tasks.add_task(
                    send_slack_response,
                    url=response_url,
                    text=f"✅ *Analysis Started!* {user}, I'm digging into research for this {linkedin_url} lead. I will notify you and update the dashboard once the plan is ready.",
                    replace_original=False
                )
            
            # 2. Start research in background (Deferred heavy import)
            from services.research_service import run_single_research
            background_tasks.add_task(run_single_research, linkedin_url=linkedin_url, user_id=internal_user_id)
        
        elif action_id == "ignore_lead":
            if response_url:
                background_tasks.add_task(
                    send_slack_response,
                    url=response_url,
                    text=f"Lead ignored by {user}.",
                    replace_original=True
                )

        return {"ok": True}

    except Exception as e:
        print(f"Error handling Slack interaction: {e}")
        return {"ok": False, "error": str(e)}

async def send_slack_response(url: str, text: str, replace_original: bool = False):
    """Helper to send response back to Slack via response_url."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "text": text,
                "replace_original": replace_original
            })
    except Exception as e:
        print(f"Error sending Slack response: {e}")

    except Exception as e:
        print(f"Error handling Slack interaction: {e}")
        return {"ok": False, "error": str(e)}
