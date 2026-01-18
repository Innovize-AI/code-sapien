import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.database import SessionLocal
from db import crud
from agents.linkedin_agent import discover_leads_from_competitor

# Configure logging
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def update_competitor_leads_job():
    logger.info("Starting scheduled daily competitor leads update...")
    async with SessionLocal() as db:
        try:
            # 1. Fetch all competitors
            competitors = await crud.get_competitors(db)
            if not competitors:
                logger.info("No competitors found to monitor. Skipping update.")
                return

            logger.info(f"Found {len(competitors)} competitors to scan.")
            
            raw_leads_to_save = []
            
            # 2. Discover leads for each
            for competitor in competitors:
                logger.info(f"Scanning competitor: {competitor.name} ({competitor.linkedin_url})")
                try:
                    leads = discover_leads_from_competitor(competitor.linkedin_url)
                    for l in leads:
                        raw_leads_to_save.append({
                            "linkedin_url": l["linkedin_url"],
                            "name": l["name"],
                            "comment": l["comment_text"],
                            "source_post": l["source_post"],
                            "source_post_url": l["source_post_url"],
                            "competitor": l["competitor"]
                        })
                except Exception as e:
                    logger.error(f"Error scanning {competitor.name}: {e}")

            # 3. Save to DB
            if raw_leads_to_save:
                logger.info(f"Saving {len(raw_leads_to_save)} newly discovered interactions...")
                await crud.batch_upsert_identified_profiles(db, raw_leads_to_save)
                logger.info("Daily update completed successfully.")
            else:
                logger.info("No new interactions found today.")
                
        except Exception as e:
            logger.error(f"Global error in daily update job: {e}")

def start_scheduler():
    # Schedule to run every 24 hours
    scheduler.add_job(update_competitor_leads_job, 'interval', hours=24)
    scheduler.start()
    logger.info("Scheduler started: Competitor discovery running every 24 hours.")
