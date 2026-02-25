from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from db.database import get_db
from db.models import AutopilotRule, ScheduledTask
from services import task_service
import os
import logging

logger = logging.getLogger(__name__)
tasks_router = APIRouter()

# Simple security check for task endpoints
TASK_SECRET = os.getenv("TASK_SECRET", "dev_secret")
logger.info(f"Task security initialized with secret: {TASK_SECRET[:4]}...")

async def verify_task_secret(x_task_secret: str = Header(None)):
    if x_task_secret != TASK_SECRET:
        logger.warning(f"Heartbeat 403: Secret mismatch. Expected: {TASK_SECRET[:4]}... Received: {x_task_secret[:4] if x_task_secret else 'None'}...")
        raise HTTPException(status_code=403, detail="Invalid task secret")

@tasks_router.post("/tasks/heartbeat")
async def tasks_heartbeat(
    db: AsyncSession = Depends(get_db), 
    _=Depends(verify_task_secret)
):
    """
    Heartbeat endpoint called by external cron (e.g., Cloud Scheduler).
    Checks all rules to see what is due and executes them.
    We use blocking await here to ensure Cloud Run stays active during processing
    without requiring "Always-on CPU" (saving costs).
    """
    import asyncio
    now = datetime.now(timezone.utc)
    tasks_run = []
    
    # Use a semaphore to limit concurrency (e.g., max 5 parallel tasks)
    sem = asyncio.Semaphore(5)

    # 1. Check Autopilot Rules (Keywords, Apollo)
    result = await db.execute(select(AutopilotRule).where(AutopilotRule.is_active == True))
    rules = result.scalars().all()
    
    async def process_rule(rule):
        async with sem:
            last_run = rule.last_run_at or (now - timedelta(days=365))
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
                
            due_at = last_run + timedelta(hours=rule.interval_hours)
            
            if now >= due_at:
                if rule.type == "keyword":
                    await task_service.keyword_discovery_task(rule_id=str(rule.id))
                elif rule.type == "apollo_config":
                    await task_service.apollo_discovery_task(rule_id=str(rule.id))
                return f"rule_{rule.id}"
            return None

    # Process all rules in parallel (blocking)
    rule_tasks = [process_rule(r) for r in rules]
    rule_results = await asyncio.gather(*rule_tasks)
    tasks_run.extend([res for res in rule_results if res])

    # 2. Check Global Scheduled Tasks (Competitor Update, HubSpot)
    result = await db.execute(select(ScheduledTask).where(ScheduledTask.is_active == True))
    global_tasks = result.scalars().all()
    
    async def process_global_task(task):
        async with sem:
            last_run = task.last_run_at or (now - timedelta(days=365))
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
                
            due_at = last_run + timedelta(hours=task.interval_hours)
            
            if now >= due_at:
                if task.name == "competitor_update":
                    await task_service.update_competitor_leads_task()
                elif task.name == "hubspot_sync":
                    await task_service.hubspot_sync_task()
                return f"global_{task.name}"
            return None

    global_task_tasks = [process_global_task(t) for t in global_tasks]
    global_results = await asyncio.gather(*global_task_tasks)
    tasks_run.extend([res for res in global_results if res])

    return {
        "status": "heartbeat_processed", 
        "tasks_run": tasks_run
    }

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
