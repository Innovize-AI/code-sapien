import asyncio
from sqlalchemy import select
from db.database import SessionLocal
from db.models import ScheduledTask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_scheduled_tasks():
    async with SessionLocal() as db:
        tasks = [
            {"name": "competitor_update", "interval_hours": 24},
            {"name": "hubspot_sync", "interval_hours": 12},
        ]
        
        for task_data in tasks:
            result = await db.execute(select(ScheduledTask).where(ScheduledTask.name == task_data["name"]))
            existing = result.scalar_one_or_none()
            
            if not existing:
                logger.info(f"Initializing scheduled task: {task_data['name']}")
                new_task = ScheduledTask(**task_data)
                db.add(new_task)
            else:
                logger.info(f"Task {task_data['name']} already exists.")
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(init_scheduled_tasks())
