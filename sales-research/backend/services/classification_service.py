import asyncio
import json
import logging
from typing import List
from sqlalchemy import select, update

logger = logging.getLogger(__name__)
from db.database import SessionLocal
from db.models import IdentifiedProfile
from db.crud import batch_upsert_identified_profiles, upsert_company, get_active_icp
from utils.activity_helper import log_activity_and_notify
from agents.linkedin_agent import batch_classify_profiles_async, enrich_company_waterfall
from agents.lead_scoring_agent import revalidate_lead_fit_async

from utils.sse_manager import event_manager

async def run_classification_and_update(raw_leads: List[dict], user_id: str | None = None):
    """
    Background task to classify leads and update DB.
    """
    from utils.url_normalize import normalize_linkedin_url
    import os
    from db.models import OrganizationSettings
    
    try:
        logger.info(f"Background Task Started for {len(raw_leads)} leads")

        # 0. Fetch Million Verifier Settings
        million_verifier_enabled = False
        async with SessionLocal() as session:
            stmt = select(OrganizationSettings).limit(1)
            result = await session.execute(stmt)
            settings = result.scalar_one_or_none()
            if settings:
                # Extract Million Verifier toggle from JSON config
                try:
                    int_config = json.loads(settings.integrations_config or "{}")
                    # Support both flat and nested structure
                    mv_config = int_config.get("million_verifier", False)
                    if isinstance(mv_config, dict):
                        million_verifier_enabled = mv_config.get("enabled", False)
                    else:
                        million_verifier_enabled = bool(mv_config)
                except:
                    million_verifier_enabled = False
                if settings.million_verifier_api_key:
                    os.environ["MILLION_VERIFIER_API_KEY"] = settings.million_verifier_api_key
                    logger.debug("Million Verifier API Key injected from DB")

        # 1. Prepare unique profiles for batch classification
        unique_profiles_map = {}
        for lead in raw_leads:
            n_url = normalize_linkedin_url(lead["linkedin_url"])
            if n_url not in unique_profiles_map:
                unique_profiles_map[n_url] = {
                    "id": n_url, # Use normalized URL as stable ID for AI
                    "headline": lead.get("headline", ""),
                    "comment": lead.get("comment", ""),
                    "source_post": lead.get("source_post", "")
                }
        
        logger.debug(f"Unique profiles to classify: {list(unique_profiles_map.keys())}")
        
        unique_profiles_list = list(unique_profiles_map.values())
        if not unique_profiles_list:
            logger.info("No unique profiles found. Returning.")
            return

        # 1.5 Filter out profiles that already exist in the database
        urls = list(unique_profiles_map.keys())
        async with SessionLocal() as session:
            result = await session.execute(
                select(IdentifiedProfile.linkedin_url).where(
                    IdentifiedProfile.linkedin_url.in_(urls),
                    IdentifiedProfile.fit_reasoning != None,
                    IdentifiedProfile.fit_reasoning != ""
                )
            )
            existing_urls = {r[0] for r in result.all()}
        
        logger.debug(f"Found {len(existing_urls)} profiles with existing classification: {existing_urls}")
        
        # Keep only profiles that are NOT in existing_urls (using normalized comparison)
        new_profiles_list = [p for p in unique_profiles_list if p["id"] not in existing_urls]
        
        logger.info(f"Processing {len(new_profiles_list)} new profiles for AI classification: {[p['id'] for p in new_profiles_list]}")
        
        # B. Handle Existing Profiles: Fetch their data and prepare for broadcast
        existing_profile_data_map = {}
        if existing_urls:
            async with SessionLocal() as session:
                existing_res = await session.execute(
                    select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url.in_(list(existing_urls)))
                )
                for p in existing_res.scalars().all():
                    existing_profile_data_map[p.linkedin_url] = {
                        "linkedin_url": p.linkedin_url,
                        "url": p.linkedin_url, # Frontend matches on .url sometimes
                        "is_fit": p.is_fit,
                        "is_competitor": p.is_competitor,
                        "is_decision_maker": p.is_decision_maker,
                        "fit_reasoning": p.fit_reasoning,
                        "intent": p.intent,
                        "sentiment": p.sentiment,
                        "name": p.name,
                        "headline": p.headline
                    }

        # IMMEDIATE BROADCAST of existing data so UI doesn't spin
        if existing_profile_data_map:
            logger.info(f"Broadcasting existing data for {len(existing_profile_data_map)} profiles immediately.")
            await event_manager.broadcast({
                "type": "classification_update",
                "leads": list(existing_profile_data_map.values())
            })

        if not new_profiles_list:
            logger.info("No profiles need AI classification. Proceeding to broadcast phase...")
            # Still proceed to process any explicitly provided raw_leads for broadcast
            new_profiles_list = []

        # 2. Process All Leads (Classify if needed, then Enrich & Broadcast)
        # We use raw_leads_to_process to ensure ALL leads passed in are considered for broadcast
        batch_size = 100
        leads_to_process = list(unique_profiles_map.values())
        
        for i in range(0, len(leads_to_process), batch_size):
            batch = leads_to_process[i : i + batch_size]
            
            # A. Identify which ones actually need AI Call
            ai_sub_batch = [p for p in batch if p["id"] in [new["id"] for new in new_profiles_list]]
            batch_res = {}
            if ai_sub_batch:
                logger.info(f"Triggering AI for sub-batch {i//batch_size + 1} ({len(ai_sub_batch)} profiles)...")
                batch_res = await batch_classify_profiles_async(ai_sub_batch)
            
            # B. Identify which leads to update from this batch
            leads_to_update_batch = []
            event_leads_batch = []

            # We don't need to re-add existing_profile_data_map here because we broadcasted them above.
            
            for lead in batch:
                lead_n_url = lead.get("id")
                # If we have an AI result, use it. Otherwise, use existing lead data.
                c = batch_res.get(lead_n_url)
                
                if c:
                    updated_data = {
                        "linkedin_url": lead_n_url,
                        "url": lead_n_url, # Ensure lead.url match works
                        "is_fit": c.get("is_fit"),
                        "is_competitor": c.get("is_competitor"),
                        "is_decision_maker": c.get("is_decision_maker"),
                        "fit_reasoning": c.get("reasoning"),
                        "intent": c.get("intent"),
                        "post_topic_depth": c.get("post_topic_depth"),
                        "sentiment": c.get("sentiment"),
                        "is_buy_signal": c.get("is_buy_signal"),
                        "is_strategic_seller": c.get("is_strategic_seller"),
                        "profile_metadata": {
                            "is_buy_signal": c.get("is_buy_signal"),
                            "is_strategic_seller": c.get("is_strategic_seller")
                        },
                        # Carry over metadata from raw lead
                        "name": lead.get("name"),
                        "headline": lead.get("headline"),
                        "comment": lead.get("comment"),
                        "source_post": lead.get("source_post"),
                        "source_post_url": lead.get("source_post_url"),
                        "competitor": lead.get("competitor")
                    }
                    leads_to_update_batch.append(updated_data)
                    event_leads_batch.append(updated_data)
                else:
                    # Even if no AI update, we still want to broadcast the current lead state
                    # Especially for manual enrichment where URL/Name might have changed
                    event_leads_batch.append(lead)

            # C/D. Save, Enrich & Notify
            if leads_to_update_batch:
                # 1. Batch Upsert Profiles (Clean isolated session)
                async with SessionLocal() as session:
                    async with session.begin():
                        icp_data = await get_active_icp(session, user_id=user_id)
                        await batch_upsert_identified_profiles(session, leads_to_update_batch)
                        
                        # Fetch IDs and current URLs for ALL leads in the batch to ensure stable identity tracking
                        profile_urls = [l["linkedin_url"] for l in event_leads_batch]
                        id_res = await session.execute(
                            select(IdentifiedProfile.id, IdentifiedProfile.linkedin_url)
                            .where(IdentifiedProfile.linkedin_url.in_(profile_urls))
                        )
                        id_map = {r[1]: str(r[0]) for r in id_res.all()}
                        for lu in event_leads_batch:
                            if lu.get("linkedin_url") in id_map:
                                lu["id"] = id_map[lu["linkedin_url"]]
                
                logger.info(f"Batch {i//batch_size + 1} - Updated {len(leads_to_update_batch)} profiles")
                
                # 2. Individual Enrichment & Notifications
                for lu in leads_to_update_batch:
                    if lu.get("is_strategic_seller"):
                        logger.info(f"Skipping notification for Strategic Seller {lu.get('name')}")
                        continue

                    # Define High Intent and Friction (Decision maker filter applied later)
                    has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point", "demo_interest"]
                    has_high_friction_topic = lu.get("post_topic_depth") in ["discovery_friction", "complaining_keywords"]
                    
                    # Logic for determining if we should even bother enriching/notifying (Apollo Costs)
                    # ONLY enrich if it is a "Hot Lead" candidate (Decision Maker + Signal)
                    is_hot_candidate = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or has_high_friction_topic)
                    
                    if is_hot_candidate:
                        # Apollo Enrichment (External Network Call - No Session Open)
                        try:
                            logger.info(f"Enriching priority lead {lu.get('name')} via Apollo...")
                            enriched = await enrich_company_waterfall(
                                person_url=lu.get("linkedin_url"),
                                million_verifier_enabled=million_verifier_enabled
                            )
                            if enriched:
                                # 3. Save Enrichment (Clean isolated sub-session)
                                async with SessionLocal() as session:
                                    async with session.begin():
                                        # Create a mutable copy for upsert_company and extract person_email
                                        company_data_for_upsert = enriched.copy()
                                        person_email = company_data_for_upsert.pop("person_email", None)
                                        email_status = company_data_for_upsert.pop("email_verification_status", None)
                                        
                                        # Enrich the lead with personal email if found
                                        if person_email:
                                            lu["email"] = person_email
                                        
                                        if email_status:
                                            lu["email_verification_status"] = email_status
                                        
                                        # PERSIST to IdentifiedProfile
                                        profile_stmt = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == lu.get("linkedin_url"))
                                        profile_res = await session.execute(profile_stmt)
                                        db_profile = profile_res.scalar_one_or_none()
                                        
                                        if db_profile:
                                            if person_email:
                                                db_profile.email = person_email
                                            if email_status:
                                                db_profile.email_verification_status = email_status
                                            
                                            # Update Identity if newly discovered from Apollo
                                            if enriched.get("person_name"):
                                                db_profile.name = enriched["person_name"]
                                                lu["name"] = enriched["person_name"]
                                            if enriched.get("headline"):
                                                db_profile.headline = enriched["headline"]
                                                lu["headline"] = enriched["headline"]
                                            if enriched.get("linkedin_url") and db_profile.linkedin_url.startswith("apollo_id:"):
                                                old_url = db_profile.linkedin_url
                                                db_profile.linkedin_url = enriched["linkedin_url"]
                                                lu["linkedin_url"] = enriched["linkedin_url"]
                                                lu["old_linkedin_url"] = old_url
                                                # Also update the ID map if needed, but the ID remains stable
                                                lu["id"] = str(db_profile.id)

                                            logger.info(f"Updated profile {db_profile.name} with email: {person_email}")

                                        # Re-define update_vals for company upsert and profile persistence
                                        update_vals = {}
                                        if person_email:
                                            update_vals["email"] = person_email
                                        if email_status:
                                            update_vals["email_verification_status"] = email_status
                                        if enriched.get("person_name"):
                                            update_vals["name"] = enriched["person_name"]
                                        if enriched.get("headline"):
                                            update_vals["headline"] = enriched["headline"]
                                        
                                        # Synchronize Metadata (mirroring enrich_leads logic)
                                        if db_profile:
                                            lu["id"] = str(db_profile.id)
                                            try:
                                                current_meta = json.loads(db_profile.profile_metadata or "{}")
                                            except:
                                                current_meta = {}
                                            
                                            current_meta.update({
                                                "person_email": person_email,
                                                "email_status": email_status,
                                                "is_enriched": True,
                                                "company_name": enriched.get("company_name"),
                                                "first_name": enriched.get("first_name"),
                                                "last_name": enriched.get("last_name"),
                                                "city": enriched.get("city"),
                                                "state": enriched.get("state"),
                                                "photo_url": enriched.get("photo_url")
                                            })
                                            update_vals["profile_metadata"] = json.dumps(current_meta)
                                            lu["profile_metadata"] = current_meta

                                        # Guard: Only upsert company if we have a valid identifier (LinkedIn URL or Domain)
                                        if enriched.get("linkedin_url") or enriched.get("domain"):
                                            try:
                                                company = await upsert_company(
                                                    session, 
                                                    company_data_for_upsert, 
                                                    linkedin_url=enriched.get("linkedin_url"),
                                                    domain=enriched.get("domain")
                                                )
                                                lu.update({
                                                    "company_id": str(company.id),
                                                    "company_name": enriched.get("company_name"),
                                                    "company_description": enriched.get("description"),
                                                    "company_industries": enriched.get("industries"),
                                                    "employee_count": enriched.get("employee_count"),
                                                    "revenue": enriched.get("revenue")
                                                })
                                                update_vals["company_id"] = company.id
                                            except Exception as upsert_e:
                                                logger.error(f"Failed to upsert company for {lu.get('name')}: {upsert_e}")
                                        else:
                                            logger.warning(f"Skipping company upsert for {lu.get('name')}: No LinkedIn URL or Domain found in enrichment data.")
                                            
                                        # 4. RE-VALIDATE Fit with confirmed firmographics (using cached icp_data)
                                        try:
                                            new_fit, new_reasoning = await revalidate_lead_fit_async(lu, enriched, icp_data)
                                            update_vals["is_fit"] = new_fit
                                            update_vals["fit_reasoning"] = new_reasoning
                                            # Update in-memory for broadcast
                                            lu["is_fit"] = new_fit
                                            lu["fit_reasoning"] = new_reasoning
                                        except Exception as re_e:
                                            logger.error(f"Error re-validating lead {lu.get('name')}: {re_e}")
                                            
                                        if update_vals:
                                            await session.execute(
                                                update(IdentifiedProfile)
                                                .where(IdentifiedProfile.linkedin_url == lu.get("linkedin_url"))
                                                .values(**update_vals)
                                            )
                        except Exception as ee:
                            logger.error(f"Error enriching lead {lu.get('name')}: {ee}")
                            
                        # FINAL CLASSIFICATION for Slack
                        # Re-check intent flags after potential local update loop
                        has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point"]
                        
                        # STRICTOR HOT LEAD: Must be a Decision Maker AND have genuine intent/signal (NOT just a hand-raiser)
                        is_hot = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or has_high_friction_topic)

                        import hashlib
                        
                        # Slack Notification (Only if fit after re-evaluation)
                        if lu.get("is_fit"):
                            lead_url = lu.get("linkedin_url")
                            current_comment = (lu.get("comment") or "").strip()
                            raw_key = f"{lead_url}:{current_comment}"
                            idempotency_key = f"lead_interaction:{hashlib.md5(raw_key.encode()).hexdigest()}"

                            # Determine Title Prefix based on seniority and intent
                            if is_hot:
                                title_prefix = "🔥 Hot Lead"
                            elif lu.get("intent") == "hand_raiser":
                                title_prefix = "🙋 Hand Raiser"
                            elif lu.get("intent") == "pain_point":
                                title_prefix = "🚨 Pain Point"
                            else:
                                title_prefix = "👀 Qualified Lead"

                            # 5. Log activity (Clean isolated sub-session)
                            async with SessionLocal() as session:
                                await log_activity_and_notify(
                                    session,
                                    type="high_potential" if is_hot else "comment",
                                    title=f"{title_prefix}: {lu.get('name') or 'Someone'} linked to {lu.get('competitor') or 'competitor'}",
                                    description=f"Intent: {lu.get('intent')} | Sentiment: {lu.get('sentiment')}\nComment: {lu.get('comment')}",
                                    metadata=lu,
                                    idempotency_key=idempotency_key
                                )

                
                # Broadcast after each batch
                await event_manager.broadcast({
                    "type": "classification_update",
                    "leads": event_leads_batch
                })
                logger.info(f"Broadcasted batch update for {len(event_leads_batch)} leads")
            else:
                 logger.debug(f"Batch {i//batch_size + 1} returned no results to update.")

    except Exception as e:
        logger.error(f"CRITICAL Error in background classification: {e}", exc_info=True)
