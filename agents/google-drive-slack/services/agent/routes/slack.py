import os
from dotenv import load_dotenv
from fastapi import APIRouter, Body, Request
from slackbot import slack_bot, handler

slack_router = APIRouter(prefix='/slack/events', tags=['slack'], responses={404: {"description": "Not found"}})

load_dotenv()

# Set Slack API credentials
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_BOT_USER_ID = os.environ.get("SLACK_BOT_USER_ID")


@slack_router.post("/")
async def slack_events(req: Request):
    """
    Route for handling slack events
    """
    print(await req.json())
    return await handler.handle(req)
    

@slack_router.get("/bot-id")
async def get_Slack_bot_id():
    """
    Get the slack bot user id
    """
    return await slack_bot.get_bot_id()
