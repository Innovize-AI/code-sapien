from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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
from routes.competitor_analysis import competitor_router
from routes.competitors import router as competitors_crud_router

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = FastAPI()

environment = os.getenv("ENVIRONMENT", "dev")  # Default to 'development' if not set



if environment == "dev":
    logger = logging.getLogger("uvicorn")
    logger.warning("Running in development mode - allowing CORS for all origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(sales_router, prefix="/sales-research")
app.include_router(history_router, prefix="/sales-research")
app.include_router(settings_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(competitor_router, prefix="/api/competitor-analysis")
app.include_router(competitors_crud_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    try:
        from scheduler import start_scheduler
        start_scheduler()
    except ImportError:
        logging.warning("APScheduler not installed. Background automation disabled.")
    except Exception as e:
        logging.error(f"Failed to start background scheduler: {e}")


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)