from fastapi import APIRouter, Header, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from db.database import get_db, SessionLocal
from db.models import AutopilotRule, ScheduledTask, Competitor
from services import task_service
import asyncio
import os
import logging
import base64
import json
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)
tasks_router = APIRouter()

# Simple security check for task endpoints
TASK_SECRET = os.getenv("TASK_SECRET", "dev_secret")
logger.info(f"Task security initialized with secret: {TASK_SECRET[:4]}...")

async def verify_task_secret(x_task_secret: str = Header(None)):
    if x_task_secret != TASK_SECRET:
        logger.warning(f"Heartbeat 403: Secret mismatch. Expected: {TASK_SECRET[:4]}... Received: {x_task_secret[:4] if x_task_secret else 'None'}...")
        raise HTTPException(status_code=403, detail="Invalid task secret")

# Pub/Sub Configuration
PUBSUB_PROJECT_ID = os.getenv("PUBSUB_PROJECT_ID")
PUBSUB_TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID", "sales-research-discovery")
LOCAL_PARALLEL = os.getenv("LOCAL_PARALLEL", "false").lower() == "true"

publisher = None
if PUBSUB_PROJECT_ID:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PUBSUB_PROJECT_ID, PUBSUB_TOPIC_ID)

async def publish_task(task_type: str, payload: dict):
    """
    Publishes a task. In an async context, we run the sync publisher in a thread.
    Returns True if published, False if fallback is needed.
    """
    if publisher and PUBSUB_PROJECT_ID:
        data = json.dumps({"type": task_type, **payload}).encode("utf-8")
        try:
            # publish() is thread-safe and non-blocking, but .result() is blocking.
            # We use to_thread to keep the event loop moving.
            future = await asyncio.to_thread(publisher.publish, topic_path, data)
            # result() waits for the server ACK
            msg_id = await asyncio.to_thread(future.result)
            logger.info(f"Published {task_type} task: {msg_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {e}")
            return False
    return False

@tasks_router.post("/tasks/heartbeat")
async def tasks_heartbeat(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_task_secret)
):
    """
    Heartbeat endpoint called by external cron.
    Dispatches tasks in PARALLEL to Pub/Sub for maximum efficiency.
    """
    import asyncio
    now = datetime.now(timezone.utc)
    tasks_to_dispatch = [] # List of (task_type, payload, fallback_func, fallback_args)
    
    # 1. Collect Autopilot Rules
    result = await db.execute(select(AutopilotRule).where(AutopilotRule.is_active == True))
    rules = result.scalars().all()
    
    for rule in rules:
        last_run = rule.last_run_at or (now - timedelta(days=365))
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
            
        if now >= (last_run + timedelta(hours=rule.interval_hours)):
            payload = {"rule_id": str(rule.id), "rule_type": rule.type}
            fallback_func = task_service.keyword_discovery_rule_task if rule.type == "keyword" else task_service.apollo_discovery_rule_task
            tasks_to_dispatch.append(("autopilot_rule", payload, fallback_func, (str(rule.id),)))

    # 2. Collect Global Scheduled Tasks
    result = await db.execute(select(ScheduledTask).where(ScheduledTask.is_active == True))
    global_tasks = result.scalars().all()
    
    for task in global_tasks:
        last_run = task.last_run_at or (now - timedelta(days=365))
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
            
        if now >= (last_run + timedelta(hours=task.interval_hours)):
            if task.name == "competitor_update":
                comp_result = await db.execute(select(Competitor))
                for comp in comp_result.scalars().all():
                    tasks_to_dispatch.append(("competitor_sync", {"competitor_id": str(comp.id)}, task_service.update_single_competitor_task, (str(comp.id),)))
                task.last_run_at = now
            else:
                fallback_func = task_service.hubspot_sync_task if task.name == "hubspot_sync" else None
                tasks_to_dispatch.append(("global_task", {"task_name": task.name}, fallback_func, ()))
                task.last_run_at = now

    # 3. Parallel Dispatch
    async def dispatch_one(t_type, t_payload, f_func, f_args):
        if await publish_task(t_type, t_payload):
            return f"{t_type}_ok"
        elif f_func:
            if LOCAL_PARALLEL:
                # Trigger as a true async task for local parallelism (ignores sequential queue)
                asyncio.create_task(f_func(*f_args))
                return f"{t_type}_local_parallel"
            else:
                # Default: FastAPI sequential background task queue
                background_tasks.add_task(f_func, *f_args)
                return f"{t_type}_local_sync"
        return f"{t_type}_skipped"

    results = []
    if tasks_to_dispatch:
        results = await asyncio.gather(*[dispatch_one(*t) for t in tasks_to_dispatch])
    
    await db.commit()
    return {
        "status": "heartbeat_processed", 
        "total_dispatched": len(results),
        "results": results
    }

@tasks_router.post("/tasks/worker")
async def tasks_worker(request: Request):
    """
    Endpoint triggered by Pub/Sub Push Subscription.
    Processes the message and performs the actual discovery work.
    """
    try:
        envelope = await request.json()
        if not envelope or "message" not in envelope:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")
        
        payload_base64 = envelope["message"]["data"]
        payload_json = base64.b64decode(payload_base64).decode("utf-8")
        data = json.loads(payload_json)
        
        task_type = data.get("type")
        logger.info(f"Worker received task: {task_type}")

        if task_type == "autopilot_rule":
            rule_id = data.get("rule_id")
            rule_type = data.get("rule_type")
            if rule_type == "keyword":
                await task_service.keyword_discovery_rule_task(rule_id)
            elif rule_type == "apollo_config":
                await task_service.apollo_discovery_rule_task(rule_id)
        
        elif task_type == "competitor_sync":
            competitor_id = data.get("competitor_id")
            await task_service.update_single_competitor_task(competitor_id)
            
        elif task_type == "global_task":
            task_name = data.get("task_name")
            if task_name == "hubspot_sync":
                await task_service.hubspot_sync_task()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Worker task failed: {e}")
        # Returning 500 triggers Pub/Sub retry
        raise HTTPException(status_code=500, detail=str(e))

@tasks_router.post("/tasks/trigger/{task_name}")
async def trigger_task(task_name: str, db: AsyncSession = Depends(get_db), _=Depends(verify_task_secret)):
    """
    Manually trigger a specific global task.
    """
    if task_name == "competitor_update":
        await task_service.update_competitor_leads_task()
    elif task_name == "hubspot_sync":
        await task_service.hubspot_sync_task()
    elif task_name == "keyword_discovery":
        await task_service.keyword_discovery_task()
    elif task_name == "apollo_discovery":
        await task_service.apollo_discovery_task()
    else:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {"status": "task_triggered", "task": task_name}
