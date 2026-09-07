from dotenv import load_dotenv
from pathlib import Path

# Base: shared keys from workflow-demos/.env
_wf_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_wf_env)

# Overrides: rfq-agent-specific values (load with override=True so local wins)
_local_env = Path(__file__).resolve().parent / ".env"
if _local_env.exists():
    load_dotenv(_local_env, override=True)

# rfq-agent defaults (only set if not already defined)
import os
os.environ.setdefault("PINECONE_INDEX",      "rfq-catalog")
os.environ.setdefault("DB_SCHEMA",           "rfq")
os.environ.setdefault("GEMINI_MODEL",        "gemini-3-flash-preview")
os.environ.setdefault("COMPANY_NAME",        "InnovizeAI")
os.environ.setdefault("REVIEWER_EMAIL",      "admin@innovizeai.com")
os.environ.setdefault("SLACK_REVIEW_CHANNEL","#rfq-review")
os.environ.setdefault("LANGCHAIN_PROJECT",   "rfq-agent")

import asyncio
import logging
import os
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(levelname)s: [%(filename)s -> %(name)s] %(message)s",
    force=True
)

if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "rfq-agent"
    logging.info(f"LangSmith tracing enabled: {os.environ['LANGCHAIN_PROJECT']}")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.rfq import router as rfq_router
from routes.webhooks import router as webhooks_router
from routes.settings import router as settings_router
from routes.emails import router as emails_router
from routes.auth import router as auth_router

app = FastAPI(title="RFQ Agent", version="1.0.0")

environment = os.getenv("ENVIRONMENT", "dev")

allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
allow_origins = [o.strip().rstrip("/") for o in allow_origins]
allow_credentials = "*" not in allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rfq_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "environment": environment}


async def _warmup_db():
    from db.database import SessionLocal
    from sqlalchemy import text
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        logging.info("DB warm-up complete.")
    except Exception as e:
        logging.warning("DB warm-up failed: %s", e)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_warmup_db())
    from services.email_watcher import start_watcher
    await start_watcher()


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)
