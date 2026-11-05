from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(levelname)s: [%(filename)s -> %(name)s] %(message)s",
    force=True,
)

if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "speed-to-lead-re-id"
    logging.info("LangSmith tracing enabled: %s", os.environ["LANGCHAIN_PROJECT"])

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from db.database import engine, Base
from db.config import SCHEMA
from services import claude, pinecone_svc, supabase_svc
from services import scheduler as scheduler_svc
from routes.webhook import router as webhook_router
from routes.dashboard import router as dashboard_router
from routes.console import router as console_router
from routes.firms import router as firms_router
from routes.plans import router as plans_router
from routes.knowledge import router as knowledge_router
from routes.brokers import router as brokers_router, dev_router as brokers_dev_router
from routes.people import router as people_router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        await conn.run_sync(Base.metadata.create_all)

    claude.init()
    pinecone_svc.init()
    supabase_svc.init()

    from db.database import SessionLocal
    from db import crud as _crud
    async with SessionLocal() as db:
        await _crud.seed_plans(db)
        await pinecone_svc.load_resource_catalogue(db)

    scheduler_svc.start()

    yield

    scheduler_svc.stop()
    await engine.dispose()


app = FastAPI(title="Speed-to-Lead — RE/ID WhatsApp AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(console_router)
app.include_router(firms_router)
app.include_router(plans_router)
app.include_router(knowledge_router)
app.include_router(brokers_router)
app.include_router(people_router)

if not settings.is_production:
    from routes.simulate import router as simulate_router
    app.include_router(simulate_router)
    app.include_router(brokers_dev_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "speed-to-lead"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
