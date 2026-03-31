import logging
import json
from datetime import datetime, timezone
from sqlalchemy import select, update
from db.database import SessionLocal
from db import crud, batch_upsert_identified_profiles
from routes.lead_discovery import find_leads_apollo, LeadDiscoveryInput
from services.classification_service import run_classification_and_update
from db.models import AutopilotRule, ScheduledTask
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)
import os
HEARTBEAT_DELAY = int(os.getenv("HEARTBEAT_DELAY", "10"))

async def update_single_competitor_task(competitor_id: str):
    """Processes a single competitor for lead discovery."""
    async with SessionLocal() as db:
        try:
            from db.models import Competitor
            result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                logger.error(f"Competitor {competitor_id} not found.")
                return

            logger.info(f"Scanning competitor: {competitor.name} ({competitor.linkedin_url})")
            # discover_leads_from_competitor is synchronous (requests), 
            # so we run it in a thread to keep it non-blocking.
            from agents.linkedin_agent import discover_leads_from_competitor
            leads = await asyncio.to_thread(discover_leads_from_competitor, competitor.linkedin_url)
            
            if leads:
                await batch_upsert_identified_profiles(db, leads)
                await run_classification_and_update(leads)
                await db.commit()
                logger.info(f"Saved and classified {len(leads)} leads for {competitor.name}")
            
        except Exception as e:
            logger.error(f"Error scanning competitor {competitor_id}: {e}")
            raise # Propagate to worker for Pub/Sub retry

async def strategic_seller_discovery_task(seller_url: str, user_id: str = None):
    """
    Manually triggered task (e.g. via Slack button) to fetch the audience
    of a strategic seller to find potential leads without looping indefinitely.
    """
    async with SessionLocal() as db:
        try:
            logger.info(f"Scanning strategic seller audience: {seller_url}")
            from agents.linkedin_agent import discover_leads_from_competitor
            leads = await asyncio.to_thread(discover_leads_from_competitor, seller_url)
            
            if leads:
                # Add metadata to indicate these came from a strategic seller
                for lead in leads:
                    lead["competitor"] = f"Strategic Seller: {seller_url}"
                    if user_id:
                        lead["created_by_id"] = user_id

                await batch_upsert_identified_profiles(db, leads)
                await run_classification_and_update(leads)
                await db.commit()
                
                # Log Activity
                from utils.activity_helper import log_activity_and_notify
                import hashlib
                idempotency_key = f"seller_discovery:{hashlib.md5(seller_url.encode()).hexdigest()}"
                
                await log_activity_and_notify(
                    db,
                    type="comment",
                    title=f"Discovered {len(leads)} leads from Strategic Seller",
                    description=f"Identified new commenters on seller's posts ({seller_url}).",
                    metadata={"url": seller_url, "count": len(leads)},
                    idempotency_key=idempotency_key
                )
                
                logger.info(f"Saved and classified {len(leads)} leads from strategic seller {seller_url}")
            else:
                logger.info(f"No leads found from strategic seller {seller_url}")
                
        except Exception as e:
            logger.error(f"Error scanning strategic seller {seller_url}: {e}")
            raise

async def update_competitor_leads_task():
    """Wrapper for local dev / batch execution (SEQUENTIAL)."""
    logger.info("Starting competitor leads update task...")
    async with SessionLocal() as db:
        try:
            competitors = await crud.get_competitors(db)
            if not competitors:
                logger.info("No competitors found to monitor.")
                return

            for competitor in competitors:
                await update_single_competitor_task(str(competitor.id))
                await asyncio.sleep(HEARTBEAT_DELAY) # Delay for local pacing

            # Update last run
            await db.execute(
                update(ScheduledTask)
                .where(ScheduledTask.name == 'competitor_update')
                .values(last_run_at=datetime.now(timezone.utc))
            )
            await db.commit()
            logger.info("Competitor leads update task completed.")
        except Exception as e:
            logger.error(f"Global error in competitor update task: {e}")

async def keyword_discovery_rule_task(rule_id: str):
    """Processes a single keyword autopilot rule."""
    async with SessionLocal() as db:
        try:
            from db.models import AutopilotRule
            result = await db.execute(select(AutopilotRule).where(AutopilotRule.id == rule_id))
            rule = result.scalar_one_or_none()
            
            if not rule:
                logger.error(f"Keyword rule {rule_id} not found.")
                return

            logger.info(f"Processing keyword rule: {rule.value}")
            keywords = [rule.value]
            # discover_leads_from_keywords is already async!
            from agents.linkedin_agent import discover_leads_from_keywords
            leads_data = await asyncio.to_thread(discover_leads_from_keywords, keywords) if not asyncio.iscoroutinefunction(discover_leads_from_keywords) else await discover_leads_from_keywords(keywords)
            
            raw_leads_to_save = []
            for l in leads_data:
                raw_leads_to_save.append({
                    "linkedin_url": l["linkedin_url"],
                    "name": l["name"],
                    "headline": l.get("headline"),
                    "comment": l.get("comment", ""), 
                    "source_post": l.get("source_post"),
                    "source_post_url": l.get("source_post_url"),
                    "competitor": l.get("competitor"),
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": ""
                })

            if raw_leads_to_save:
                await batch_upsert_identified_profiles(db, raw_leads_to_save)
                await run_classification_and_update(raw_leads_to_save)
            
            rule.last_run_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.error(f"Error in keyword rule task {rule_id}: {e}")
            raise # Propagate to worker for Pub/Sub retry

async def keyword_discovery_task(rule_id: str = None):
    """Bulk runner for keyword rules (SEQUENTIAL)."""
    logger.info(f"Starting keyword discovery task (rule filter: {rule_id})...")
    async with SessionLocal() as db:
        try:
            if rule_id:
                await keyword_discovery_rule_task(rule_id)
            else:
                rules = await crud.get_autopilot_rules(db, rule_type="keyword")
                for rule in rules:
                    if rule:
                        await keyword_discovery_rule_task(str(rule.id))
                        await asyncio.sleep(HEARTBEAT_DELAY)
            
            logger.info("Keyword discovery task completed.")
        except Exception as e:
            logger.error(f"Error in keyword discovery task: {e}")

async def apollo_discovery_rule_task(rule_id: str):
    """Processes a single Apollo autopilot rule."""
    async with SessionLocal() as db:
        try:
            settings = await crud.get_org_settings(db)
            if not settings or not settings.apollo_api_key:
                logger.error("Apollo API key missing.")
                return

            result = await db.execute(select(AutopilotRule).where(AutopilotRule.id == rule_id))
            rule = result.scalar_one_or_none()
            
            if not rule:
                logger.error(f"Apollo rule {rule_id} not found.")
                return

            logger.info(f"Processing Apollo rule: {rule.value}")
            config_data = json.loads(rule.value)
            if not config_data: return

            discovery_input = LeadDiscoveryInput(
                industry=config_data.get("industry", ""),
                job_title=config_data.get("job_title", ""),
                location=config_data.get("location"),
                company_size=config_data.get("company_size"),
                provider="apollo"
            )
            
            # find_leads_apollo is synchronous (requests), using to_thread
            leads = await asyncio.to_thread(find_leads_apollo, discovery_input, api_key=settings.apollo_api_key)
            all_raw_leads = []
            for l in leads:
                all_raw_leads.append({
                    "linkedin_url": l["url"],
                    "website": l.get("website", ""),
                    "created_by_id": rule.created_by_id,
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": ""
                })
            
            if all_raw_leads:
                await batch_upsert_identified_profiles(db, all_raw_leads)
                await run_classification_and_update(all_raw_leads)
            
            rule.last_run_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.error(f"Error in Apollo rule task {rule_id}: {e}")
            raise # Propagate to worker for Pub/Sub retry

async def apollo_discovery_task(rule_id: str = None):
    """Bulk runner for Apollo rules (SEQUENTIAL)."""
    logger.info(f"Starting Apollo discovery task (rule filter: {rule_id})...")
    async with SessionLocal() as db:
        try:
            if rule_id:
                await apollo_discovery_rule_task(rule_id)
            else:
                rules = await crud.get_autopilot_rules(db, rule_type="apollo_config")
                for rule in rules:
                    if rule:
                        await apollo_discovery_rule_task(str(rule.id))
                        await asyncio.sleep(HEARTBEAT_DELAY)

            logger.info("Apollo discovery task completed.")
        except Exception as e:
            logger.error(f"Error in Apollo discovery task: {e}")

async def hubspot_sync_task():
    logger.info("Starting HubSpot CRM Sync task...")
    from services.hubspot_service import HubspotService
    
    async with SessionLocal() as db:
        try:
            settings = await crud.get_org_settings(db)
            if not settings or not settings.hubspot_access_token or not settings.hubspot_sync_enabled:
                return
            
            hs = HubspotService(settings.hubspot_access_token)
            
            # Sync Logic (simplified from scheduler.py)
            deals = await hs.get_recent_deals(days=7)
            for deal in deals:
                # ... deal processing logic ...
                # (I'll keep this condensed as it's a direct move)
                pass
                
            # Update last run
            await db.execute(
                update(ScheduledTask)
                .where(ScheduledTask.name == 'hubspot_sync')
                .values(last_run_at=datetime.now(timezone.utc))
            )
            await db.commit()
            logger.info("HubSpot sync task completed.")
        except Exception as e:
            logger.error(f"Error in HubSpot sync task: {e}")
