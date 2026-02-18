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

async def hubspot_sync_job():
    logger.info("Starting HubSpot CRM Sync job...")
    from services.hubspot_service import HubspotService
    from db.models import CRMContext
    from sqlalchemy import select
    
    async with SessionLocal() as db:
        try:
            settings = await crud.get_org_settings(db)
            if not settings or not settings.hubspot_access_token or not settings.hubspot_sync_enabled:
                logger.info("HubSpot integration not configured or disabled. Skipping.")
                return
            
            hs = HubspotService(settings.hubspot_access_token)
            
            # 1. Sync Deals & Champions
            logger.info("Syncing recent HubSpot deals...")
            deals = await hs.get_recent_deals(days=7)
            for deal in deals:
                deal_id = deal["id"]
                props = deal["properties"]
                stage = props.get("dealstage")
                
                # Get associated contacts
                contacts = await hs.get_deal_contacts(deal_id)
                for contact in contacts:
                    c_props = contact["properties"]
                    email = c_props.get("email")
                    li_url = c_props.get("linkedin_url")
                    
                    # Determine context type
                    context_type = "customer" if stage == "closedwon" else "lost_deal" if stage == "closedlost" else "active_prospect"
                    
                    # Competitor Discovery from Lost Deals
                    competitor_mentions = []
                    lost_reason = props.get("closed_lost_reason") or ""
                    if lost_reason:
                        # Simple extraction logic - look for capitalized words that might be company names
                        # or specific keywords. In a real scenario, use LLM or a list.
                        common_competitors = ["clay", "apollo", "zoominfo", "salesforce", "outreach", "salesloft"]
                        for comp in common_competitors:
                            if comp in lost_reason.lower():
                                competitor_mentions.append(comp)
                                logger.info(f"Potential competitor found in HubSpot deal {deal_id}: {comp}")

                    # Store context
                    context_data = {
                        "email": email,
                        "linkedin_url": li_url,
                        "hubspot_contact_id": contact["id"],
                        "type": context_type,
                        "deal_name": props.get("dealname"),
                        "deal_stage": stage,
                        "closed_lost_reason": lost_reason,
                        "original_company": c_props.get("company"),
                        "extra_metadata": json.dumps({"competitors": competitor_mentions}) if competitor_mentions else None
                    }
                    
                    # Upsert CRM Context
                    await crud.upsert_crm_context(db, context_data)
            
            # 2. Sync Web Visits as Signals
            logger.info("Syncing HubSpot Web Vist signals...")
            visits = await hs.get_web_visits(days=1)
            for visit in visits:
                # Process intense signals (multiple views or specific pages)
                # Implementation depends on event payload structure
                pass
                
            logger.info("HubSpot sync job completed.")
        except Exception as e:
            logger.error(f"Error in HubSpot sync job: {e}")

def start_scheduler():
    # Schedule all discovery jobs to run every 24 hours
    scheduler.add_job(update_competitor_leads_job, 'interval', hours=24)
    scheduler.add_job(keyword_discovery_job, 'interval', hours=24)
    scheduler.add_job(apollo_discovery_job, 'interval', hours=24)
    scheduler.add_job(hubspot_sync_job, 'interval', hours=12) # More frequent for signals
    
    scheduler.start()
    logger.info("Scheduler started: All signals and discovery jobs active.")

