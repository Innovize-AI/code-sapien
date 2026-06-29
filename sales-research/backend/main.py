from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import os, sys

logging.basicConfig(
    stream=sys.stdout, 
    level=logging.INFO,
    format="%(levelname)s: [%(filename)s -> %(name)s] %(message)s",
    force=True
)

# LangSmith Tracking Configuration
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "sales-research"
    logging.info(f"🚀 LangSmith Tracing enabled in project: {os.environ['LANGCHAIN_PROJECT']}")
else:
    logging.warning("⚠️ LangSmith API Key not found. Tracing disabled.")

import uvicorn
# from app.api.routers.chat import chat_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.sales_research import sales_router
from routes.history import history_router
from routes.settings import settings_router
from routes.dashboard import dashboard_router
from routes.webhooks import webhooks_router
from routes.integrations_kit import kit_router
from fastapi.staticfiles import StaticFiles
from routes.competitor_analysis import competitor_router
from routes.competitors import router as competitors_crud_router
from routes.activities import activities_router
from routes.slack_interactions import slack_interactions_router
from routes.knowledge import router as knowledge_router
from routes.autopilot import autopilot_router
from routes.tasks import tasks_router
from routes.companies import router as companies_router

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

environment = os.getenv("ENVIRONMENT", "dev")  # Default to 'development' if not set



# Configure CORS
allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
# Strip whitespace and trailing slashes from origins
allow_origins = [origin.strip().rstrip("/") for origin in allow_origins]

# Starlette/FastAPI: allow_credentials=True cannot be used with allow_origins=["*"]
allow_credentials = True
if "*" in allow_origins:
    allow_credentials = False

if environment == "dev":
    logger = logging.getLogger("uvicorn")
    logger.warning("CORS Configuration: origins=%s, credentials=%s", allow_origins, allow_credentials)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales_router, prefix="/sales-research")
app.include_router(history_router, prefix="/sales-research")
app.include_router(settings_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
from routes.webhooks import webhooks_router as wh_router
app.include_router(wh_router, prefix="/api")
app.include_router(kit_router, prefix="/api")
app.include_router(competitor_router, prefix="/api/competitor-analysis")
app.include_router(competitors_crud_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api/knowledge")
app.include_router(slack_interactions_router)
app.include_router(autopilot_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
from routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth")

from routes.trial import router as trial_router
app.include_router(trial_router, prefix="/api/trial")

@app.get("/api/config")
async def get_global_config():
    return {
        "trial_mode": os.getenv("TRIAL_MODE", "false").lower() == "true",
        "environment": os.getenv("ENVIRONMENT", "dev")
    }

async def _warmup_db():
    """
    Pre-open pool connections and seed the Postgres query planner cache.
    Fires the most common aggregate queries in parallel so the first real
    user request never pays the TCP-connect + planner cost.
    """
    from db.database import SessionLocal
    from db.models import ResearchReport, IdentifiedProfile, Profile
    from sqlalchemy import select, func

    async def _ping(idx: int):
        try:
            async with SessionLocal() as s:
                # These are the hottest queries across stats / history / usage / analytics
                await s.execute(select(func.count()).select_from(ResearchReport))
                await s.execute(select(func.count()).select_from(IdentifiedProfile))
                if idx == 0:
                    # Seed the profiles planner path too (used by get_current_user)
                    await s.execute(select(func.count()).select_from(Profile))
        except Exception as e:
            logging.warning("DB warm-up connection %d failed: %s", idx, e)

    # Open 5 connections in parallel — enough to saturate the most common burst
    await asyncio.gather(*[_ping(i) for i in range(5)])
    logging.info("DB warm-up complete — pool pre-seeded, planner cache warmed.")


@app.on_event("startup")
async def startup_event():
    # Warm up DB connections and query planner in the background so the
    # server is ready to serve without blocking on the first user request.
    asyncio.create_task(_warmup_db())

    if environment == "dev":
        try:
            from scheduler import start_scheduler
            start_scheduler()
            logging.info("APScheduler started (dev mode).")
        except ImportError:
            logging.warning("APScheduler not installed. Background automation disabled.")
        except Exception as e:
            logging.error(f"Failed to start background scheduler: {e}")
    else:
        logging.info("Running in production/staging. APScheduler disabled (relying on Google Cloud Scheduler).")


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)