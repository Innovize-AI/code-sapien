import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.database import SessionLocal
from db import crud, batch_upsert_identified_profiles
from agents.linkedin_agent import discover_leads_from_competitor, discover_leads_from_keywords
from routes.lead_discovery import find_leads_apollo, LeadDiscoveryInput
from services.classification_service import run_classification_and_update
import json


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

async def keyword_discovery_job():
    logger.info("Starting scheduled keyword discovery job...")
    async with SessionLocal() as db:
        try:
            # Fetch all active keyword rules
            rules = await crud.get_autopilot_rules(db, rule_type="keyword")
            if not rules:
                logger.info("No keyword rules found in AutopilotRule table. Skipping.")
                return
            
            keywords = [r.value for r in rules]
            logger.info(f"Searching for leads with keywords from {len(rules)} rules: {keywords}")
            leads_data = await discover_leads_from_keywords(keywords)
            
            raw_leads_to_save = []
            for l in leads_data:
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "headline": l.get("headline"),
                    "comment": l.get("comment_text", ""), 
                    "source_post": l.get("source_post"),
                    "source_post_url": l.get("source_post_url"),
                    "competitor": l.get("competitor"),
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": ""
                })

            if raw_leads_to_save:
                logger.info(f"Saving {len(raw_leads_to_save)} leads from keyword search...")
                await batch_upsert_identified_profiles(db, raw_leads_to_save)
                # Background classification
                await run_classification_and_update(raw_leads_to_save)
                logger.info("Keyword discovery and classification completed.")
            else:
                logger.info("No new leads found for keywords today.")
                
        except Exception as e:
            logger.error(f"Error in keyword discovery job: {e}")

async def apollo_discovery_job():
    logger.info("Starting scheduled Apollo discovery job...")
    async with SessionLocal() as db:
        try:
            # Fetch global settings for API key
            settings = await crud.get_org_settings(db)
            if not settings or not settings.apollo_api_key:
                logger.info("No Apollo API key found in settings. Skipping.")
                return

            rules = await crud.get_autopilot_rules(db, rule_type="apollo_config")
            if not rules:
                logger.info("No Apollo config rules found in AutopilotRule table. Skipping.")
                return
            
            all_raw_leads = []
            for rule in rules:
                try:
                    config_data = json.loads(rule.value)
                    if not config_data: continue

                    logger.info(f"Searching Apollo with rule attribution (creator: {rule.created_by_id}) config: {config_data}")
                    
                    # Map config to LeadDiscoveryInput
                    discovery_input = LeadDiscoveryInput(
                        industry=config_data.get("industry", ""),
                        job_title=config_data.get("job_title", ""),
                        location=config_data.get("location"),
                        company_size=config_data.get("company_size"),
                        provider="apollo"
                    )
                    
                    leads = find_leads_apollo(discovery_input, api_key=settings.apollo_api_key)
                    for l in leads:
                        all_raw_leads.append({
                            "linkedin_url": l["url"],
                            "website": l.get("website", ""),
                            "created_by_id": rule.created_by_id, # Attributing lead to the rule creator
                            "is_fit": False,
                            "is_competitor": False,
                            "is_decision_maker": False,
                            "fit_reasoning": ""
                        })
                except Exception as e:
                    logger.error(f"Error processing Apollo rule {rule.id}: {e}")

            if all_raw_leads:
                logger.info(f"Saving {len(all_raw_leads)} leads from Apollo search...")
                await batch_upsert_identified_profiles(db, all_raw_leads)
                # Background classification
                await run_classification_and_update(all_raw_leads)
                logger.info("Apollo discovery and classification completed.")
            else:
                logger.info("No new leads found on Apollo today.")
                
        except Exception as e:
            logger.error(f"Error in Apollo discovery job: {e}")

def start_scheduler():
    # Schedule all discovery jobs to run every 24 hours
    scheduler.add_job(update_competitor_leads_job, 'interval', hours=24)
    scheduler.add_job(keyword_discovery_job, 'interval', hours=24)
    scheduler.add_job(apollo_discovery_job, 'interval', hours=24)
    
    scheduler.start()
    logger.info("Scheduler started: All Autopilot discovery jobs running every 24 hours.")

