import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services import task_service
import os

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Only run in-process scheduler if we are in development mode
    # and not running in a multi-worker environment.
    environment = os.getenv("ENVIRONMENT", "dev")
    if environment != "dev":
        logger.info("Production environment detected. Skipping in-process scheduler (use heartbeat instead).")
        return

    # Schedule discovery jobs using the extracted task logic
    scheduler.add_job(task_service.update_competitor_leads_task, 'interval', hours=24)
    scheduler.add_job(task_service.keyword_discovery_task, 'interval', hours=24)
    scheduler.add_job(task_service.apollo_discovery_task, 'interval', hours=24)
    scheduler.add_job(task_service.hubspot_sync_task, 'interval', hours=12)
    
    scheduler.start()
    logger.info("Local development scheduler started.")
