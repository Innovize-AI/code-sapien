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

            # Trial Mode Safety Check
            from utils.trial_utils import check_trial_lead_limit
            if await check_trial_lead_limit(db, org_id=competitor.organization_id, user_id=competitor.created_by_id):
                logger.info(f"Skipping competitor scan {competitor.name} - Trial Limit Reached.")
                return

            logger.info(f"Scanning competitor: {competitor.name} ({competitor.linkedin_url})")
            # discover_leads_from_competitor is synchronous (requests), 
            # so we run it in a thread to keep it non-blocking.
            from agents.linkedin_agent import discover_leads_from_competitor
            leads = await asyncio.to_thread(discover_leads_from_competitor, competitor.linkedin_url)
            
            if leads:
                await batch_upsert_identified_profiles(
                    db, 
                    leads, 
                    user_id=str(competitor.created_by_id) if competitor.created_by_id else None,
                    org_id=competitor.organization_id
                )
                await db.commit()
                # Run classification AFTER commit to prevent deadlocks
                await run_classification_and_update(
                    leads, 
                    user_id=str(competitor.created_by_id) if competitor.created_by_id else None,
                    org_id=competitor.organization_id
                )
                logger.info(f"Saved and classified {len(leads)} leads for {competitor.linkedin_url}")
            
        except Exception as e:
            logger.error(f"Error scanning competitor {competitor_id}: {e}")
            raise # Propagate to worker for Pub/Sub retry

async def strategic_seller_discovery_task(seller_url: str, user_id: str = None, org_id: str = None):
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
                    if org_id:
                        lead["organization_id"] = org_id

                await batch_upsert_identified_profiles(db, leads)
                await db.commit()
                # Run classification AFTER commit to prevent deadlocks
                await run_classification_and_update(leads, user_id=user_id, org_id=org_id)
                
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
                    idempotency_key=idempotency_key,
                    org_id=org_id,
                    user_id=user_id
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

            # Trial Mode Safety Check
            from utils.trial_utils import check_trial_lead_limit
            if await check_trial_lead_limit(db, org_id=rule.organization_id, user_id=rule.created_by_id):
                logger.info(f"Skipping keyword rule {rule.id} - Trial Limit Reached.")
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
                    "fit_reasoning": "",
                    "created_by_id": rule.created_by_id,
                    "organization_id": rule.organization_id
                })

            if raw_leads_to_save:
                await batch_upsert_identified_profiles(
                    db, 
                    raw_leads_to_save,
                    user_id=str(rule.created_by_id),
                    org_id=rule.organization_id
                )
            
            rule.last_run_at = datetime.now(timezone.utc)
            await db.commit()

            # Run classification AFTER commit to prevent deadlocks
            if raw_leads_to_save:
                await run_classification_and_update(
                    raw_leads_to_save, 
                    user_id=str(rule.created_by_id),
                    org_id=rule.organization_id
                )
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
            result = await db.execute(select(AutopilotRule).where(AutopilotRule.id == rule_id))
            rule = result.scalar_one_or_none()
            
            if not rule:
                logger.error(f"Apollo rule {rule_id} not found.")
                return

            # Trial Mode Safety Check
            from utils.trial_utils import check_trial_lead_limit
            if await check_trial_lead_limit(db, org_id=rule.organization_id, user_id=rule.created_by_id):
                logger.info(f"Skipping Apollo rule {rule.id} - Trial Limit Reached.")
                return

            settings = await crud.get_org_settings(db, user_id=str(rule.created_by_id), org_id=rule.organization_id)
            if not settings or not settings.apollo_api_key:
                logger.error(f"Apollo API key missing for owner {rule.created_by_id}.")
                return

            logger.info(f"Processing Apollo rule: {rule.value}")
            config_data = json.loads(rule.value)
            if not config_data: return

            # Pagination Logic: Fetch the next page each day
            last_page = config_data.get("last_page_searched", 0)
            next_page = last_page + 1
            logger.info(f"Apollo Discovery: Fetching page {next_page} for rule {rule_id}")

            # Construct input with all available filters
            discovery_input = LeadDiscoveryInput(
                provider="apollo",
                industry=config_data.get("industry"),
                job_title=config_data.get("job_title"),
                location=config_data.get("location"),
                company_size=config_data.get("company_size"),
                # Advanced filters
                person_titles=config_data.get("person_titles"),
                person_seniorities=config_data.get("person_seniorities"),
                person_locations=config_data.get("person_locations"),
                organization_locations=config_data.get("organization_locations"),
                organization_domains=config_data.get("organization_domains"),
                contact_email_status=config_data.get("contact_email_status"),
                organization_num_employees_ranges=config_data.get("organization_num_employees_ranges"),
                revenue_min=config_data.get("revenue_min"),
                revenue_max=config_data.get("revenue_max"),
                currently_using_any_of_technology_uids=config_data.get("currently_using_any_of_technology_uids"),
                q_organization_job_titles=config_data.get("q_organization_job_titles")
            )
            
            # find_leads_apollo is synchronous (requests), using to_thread
            leads = await asyncio.to_thread(find_leads_apollo, discovery_input, api_key=settings.apollo_api_key, page=next_page)
            all_raw_leads = []
            for l in leads:
                all_raw_leads.append({
                    "linkedin_url": l["url"],
                    "website": l.get("website", ""),
                    "created_by_id": rule.created_by_id,
                    "organization_id": rule.organization_id,
                    "competitor": "Apollo", # Tag for filtering in the dashboard
                    "is_fit": False,
                    "is_competitor": False,
                    "is_decision_maker": False,
                    "fit_reasoning": "",
                    "source_post": "Apollo Discovery Rule",
                    "source_post_url": "https://apollo.io"
                })
            
            if all_raw_leads:
                await batch_upsert_identified_profiles(
                    db, 
                    all_raw_leads,
                    user_id=str(rule.created_by_id),
                    org_id=rule.organization_id
                )
            
            # Update pagination and last run
            config_data["last_page_searched"] = next_page
            rule.value = json.dumps(config_data)
            rule.last_run_at = datetime.now(timezone.utc)
            await db.commit()

            # Run classification AFTER commit
            if all_raw_leads:
                await run_classification_and_update(
                    all_raw_leads, 
                    user_id=str(rule.created_by_id),
                    org_id=rule.organization_id
                )
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

async def sync_single_organization_hubspot(settings_id: str):
    """Syncs HubSpot for a specific organization settings entry."""
    from services.hubspot_service import HubspotService
    from db.models import OrganizationSettings
    
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(OrganizationSettings).where(OrganizationSettings.id == settings_id))
            settings = result.scalar_one_or_none()
            
            if not settings or not settings.hubspot_access_token:
                logger.error(f"HubSpot sync failed: Settings {settings_id} not found or missing token.")
                return

            logger.info(f"Syncing HubSpot for Org: {settings.organization_id}")
            hs = HubspotService(settings.hubspot_access_token)
            
            # Match recent deals (or other sync logic)
            deals = await hs.get_recent_deals(days=7)
            # ... process deals ...
            logger.info(f"HubSpot sync successful for Org: {settings.organization_id}")
        except Exception as e:
            logger.error(f"Error in single HubSpot sync for {settings_id}: {e}")
            raise

async def hubspot_sync_task():
    # Skip for trial mode as requested
    if os.getenv("TRIAL_MODE", "false").lower() == "true":
        logger.info("Skipping HubSpot CRM Sync in Trial Mode.")
        return

    async with SessionLocal() as db:
        try:
            # Multi-tenant sync: Find all settings with HubSpot enabled
            from db.models import OrganizationSettings
            result = await db.execute(
                select(OrganizationSettings.id).where(
                    OrganizationSettings.hubspot_access_token.isnot(None),
                    OrganizationSettings.hubspot_sync_enabled == True
                )
            )
            settings_ids = result.scalars().all()
            
            # In a scalable setup, the heartbeat should dispatch these.
            # If running locally/fallback, we do them sequentially.
            for sid in settings_ids:
                await sync_single_organization_hubspot(str(sid))
                await asyncio.sleep(1) # Small delay between orgs

            # Update last run
            await db.execute(
                update(ScheduledTask)
                .where(ScheduledTask.name == 'hubspot_sync')
                .values(last_run_at=datetime.now(timezone.utc))
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Global error in HubSpot discovery task: {e}")
