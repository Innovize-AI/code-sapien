from dotenv import load_dotenv

load_dotenv()

import logging
import os, sys

# LangSmith Tracking Configuration
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "sales-research"
    print(f"🚀 LangSmith Tracing enabled in project: {os.environ['LANGCHAIN_PROJECT']}")
else:
    print("⚠️ LangSmith API Key not found. Tracing disabled.")

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

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

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
from routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth")

@app.on_event("startup")
async def startup_event():
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