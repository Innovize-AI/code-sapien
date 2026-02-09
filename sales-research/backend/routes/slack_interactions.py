import json
from fastapi import APIRouter, Request, BackgroundTasks, Form
from typing import Optional
from services.research_service import run_single_research
import httpx

slack_interactions_router = APIRouter(tags=['Slack Interactions'], responses={404: {"description": "Not found"}},)

@slack_interactions_router.post("/slack/interactions")
async def handle_slack_interactions(
    background_tasks: BackgroundTasks,
    payload: str = Form(...)
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

        if action_id == "analyze_lead" and linkedin_url:
            # 1. Start research in background
            background_tasks.add_task(run_single_research, linkedin_url=linkedin_url)
            
            # 2. Respond to Slack in background (to avoid 3s timeout)
            if response_url:
                background_tasks.add_task(
                    send_slack_response,
                    url=response_url,
                    text=f"✅ *Analysis Started!* {user}, I'm digging into research for this {linkedin_url}lead. I will notify you and update the dashboard once the plan is ready.",
                    replace_original=False
                )
        
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
