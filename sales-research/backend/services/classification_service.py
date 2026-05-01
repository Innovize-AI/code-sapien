import asyncio
import json
import logging
import os
from typing import List
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

from db.database import SessionLocal
from db.models import IdentifiedProfile, OrganizationSettings, Company
from db.crud import batch_upsert_identified_profiles, upsert_company, get_active_icp
from utils.activity_helper import log_activity_and_notify
from agents.linkedin_agent import batch_classify_profiles_async, enrich_company_waterfall
from agents.lead_scoring_agent import revalidate_lead_fit_async
from utils.sse_manager import event_manager
from utils.trial_utils import check_trial_classification_limit

async def check_classification_limit(user_id: str) -> bool:
    """
    Checks if a trial user has reached their identified profile classification limit.
    Returns True if limit reached, False otherwise.
    """
    async with SessionLocal() as db:
        return await check_trial_classification_limit(db, org_id=None, user_id=user_id)

async def run_classification_and_update(raw_leads: List[dict], user_id: str | None = None, org_id: str | None = None):
    """
    Background task to classify leads and update DB.
    """
    from utils.url_normalize import normalize_linkedin_url
    
    try:
        logger.info(f"Background Task Started for {len(raw_leads)} leads for Org: {org_id}")

        # 0. Fetch Settings
        million_verifier_enabled = False
        company_context = None
        async with SessionLocal() as session:
            if org_id:
                stmt = select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
            else:
                stmt = select(OrganizationSettings).limit(1)
                
            result = await session.execute(stmt)
            settings = result.scalar_one_or_none()
            if settings:
                trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
                if trial_mode and os.getenv("MILLION_VERIFIER_API_KEY"):
                    million_verifier_enabled = True
                else:
                    try:
                        int_config = json.loads(settings.integrations_config or "{}")
                        mv_config = int_config.get("million_verifier", False)
                        if isinstance(mv_config, dict):
                            million_verifier_enabled = mv_config.get("enabled", False)
                        else:
                            million_verifier_enabled = bool(mv_config)
                    except:
                        million_verifier_enabled = False
                
                if trial_mode:
                    million_verifier_key = os.getenv("MILLION_VERIFIER_API_KEY")
                    if million_verifier_key:
                        os.environ["MILLION_VERIFIER_API_KEY"] = million_verifier_key
                        logger.debug("Million Verifier API Key injected from environment (Trial Mode)")
                elif settings.million_verifier_api_key:
                    os.environ["MILLION_VERIFIER_API_KEY"] = settings.million_verifier_api_key
                    logger.debug("Million Verifier API Key injected from DB")

                # Build dynamic company context
                if settings.selling_profile_json:
                    try:
                        sp_data = json.loads(settings.selling_profile_json)
                        c_name = sp_data.get("company_name", "Our Company")
                        c_desc = sp_data.get("description", "")
                        products = sp_data.get("products", [])
                        
                        prod_text = ""
                        for p in products:
                            p_name = p.get("name")
                            p_desc = p.get("description")
                            if p_name:
                                prod_text += f"\n- {p_name}: {p_desc}"
                        
                        company_context = f"Company: {c_name}\nDescription: {c_desc}\nProducts We Sell:{prod_text}"
                    except Exception as e:
                        logger.error(f"Error building company context: {e}")

        # 1. Prepare unique profiles for batch classification
        unique_profiles_map = {}
        for lead in raw_leads:
            l_url = lead.get("linkedin_url") or lead.get("url")
            if not l_url:
                continue
            n_url = normalize_linkedin_url(l_url)
            if n_url not in unique_profiles_map:
                unique_profiles_map[n_url] = {
                    "id": n_url,
                    "headline": lead.get("headline", ""),
                    "comment": lead.get("comment", ""),
                    "source_post": lead.get("source_post", ""),
                    "name": lead.get("name"),
                    "source_post_url": lead.get("source_post_url"),
                    "competitor": lead.get("competitor")
                }
        
        unique_profiles_list = list(unique_profiles_map.values())
        if not unique_profiles_list:
            logger.info("No unique profiles to process.")
            return

        # 1.5 Filter out profiles that already exist with classification
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
        
        # B. Handle Existing Profiles: Prep for broadcast
        existing_profile_data_map = {}
        if existing_urls:
            async with SessionLocal() as session:
                existing_res = await session.execute(
                    select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url.in_(list(existing_urls)))
                )
                for p in existing_res.scalars().all():
                    existing_profile_data_map[p.linkedin_url] = {
                        "id": str(p.id),
                        "linkedin_url": p.linkedin_url,
                        "url": p.linkedin_url,
                        "is_fit": p.is_fit,
                        "is_competitor": p.is_competitor,
                        "is_decision_maker": p.is_decision_maker,
                        "fit_reasoning": p.fit_reasoning,
                        "intent": p.intent,
                        "sentiment": p.sentiment,
                        "name": p.name,
                        "headline": p.headline
                    }

        if existing_profile_data_map:
            await event_manager.broadcast({
                "type": "classification_update",
                "leads": list(existing_profile_data_map.values())
            }, org_id=org_id)

        # 2. Process Batches
        batch_size = 100
        leads_to_process = list(unique_profiles_map.values())
        new_profiles_list = [p for p in leads_to_process if p["id"] not in existing_urls]
        
        for i in range(0, len(leads_to_process), batch_size):
            batch = leads_to_process[i : i + batch_size]
            
            # Identify which ones need AI Call
            ai_sub_batch = [p for p in batch if p["id"] in [new["id"] for new in new_profiles_list]]
            batch_res = {}
            if ai_sub_batch:
                if await check_classification_limit(user_id):
                    logger.info(f"Trial limit reached. Skipping AI for {len(ai_sub_batch)} leads.")
                else:
                    logger.info(f"Triggering AI for {len(ai_sub_batch)} profiles...")
                    batch_res = await batch_classify_profiles_async(ai_sub_batch, company_context=company_context)
            logger.info(f"batch res response: {batch_res}")
            leads_to_update_batch = []
            event_leads_batch = []
            
            for lead in batch:
                lead_n_url = lead.get("id") or lead.get("linkedin_url")
                c = batch_res.get(lead_n_url)
                
                if c:
                    logger.debug(f"Classifying {lead_n_url}: Result type={type(c)}")
                    # Helper to get values from c (could be dict or Pydantic object)
                    def get_val(obj, key, default=None):
                        if isinstance(obj, dict):
                            return obj.get(key, default)
                        return getattr(obj, key, default)

                    updated_data = {
                        "linkedin_url": lead_n_url,
                        "url": lead_n_url,
                        "is_fit": get_val(c, "is_fit", False),
                        "is_competitor": get_val(c, "is_competitor", False),
                        "is_decision_maker": get_val(c, "is_decision_maker", False),
                        "fit_reasoning": get_val(c, "reasoning", ""),
                        "intent": get_val(c, "intent", "low_signal"),
                        "post_topic_depth": get_val(c, "post_topic_depth", "generic_engagement"),
                        "sentiment": get_val(c, "sentiment", "neutral"),
                        "is_buy_signal": get_val(c, "is_buy_signal", False),
                        "is_strategic_seller": get_val(c, "is_strategic_seller", False),
                        "profile_metadata": {
                            "is_buy_signal": get_val(c, "is_buy_signal", False),
                            "is_strategic_seller": get_val(c, "is_strategic_seller", False),
                            "post_topic_depth": get_val(c, "post_topic_depth"),
                            "intent": get_val(c, "intent")
                        },
                        "name": lead.get("name"),
                        "headline": lead.get("headline"),
                        "comment": lead.get("comment"),
                        "source_post": lead.get("source_post"),
                        "source_post_url": lead.get("source_post_url"),
                        "competitor": lead.get("competitor"),
                        "old_linkedin_url": lead.get("old_linkedin_url")
                    }
                    leads_to_update_batch.append(updated_data)
                    event_leads_batch.append(updated_data)
                else:
                    event_leads_batch.append(lead)

            if leads_to_update_batch:
                # 1. Batch Upsert
                async with SessionLocal() as session:
                    async with session.begin():
                        icp_data = await get_active_icp(session, user_id=user_id)
                        await batch_upsert_identified_profiles(
                            session, 
                            leads_to_update_batch,
                            user_id=user_id,
                            org_id=org_id
                        )
                        
                        # Fetch IDs for ID map
                        profile_urls = [l["linkedin_url"] for l in event_leads_batch]
                        id_res = await session.execute(
                            select(IdentifiedProfile.id, IdentifiedProfile.linkedin_url)
                            .where(IdentifiedProfile.linkedin_url.in_(profile_urls))
                        )
                        id_map = {r[1]: str(r[0]) for r in id_res.all()}
                        for lu in event_leads_batch:
                            if lu.get("linkedin_url") in id_map:
                                lu["id"] = id_map[lu["linkedin_url"]]
                
                # 2. Individual Enrichment & Notifications
                for lu in leads_to_update_batch:
                    if lu.get("is_strategic_seller"):
                        continue

                    has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point", "demo_interest"]
                    has_high_friction_topic = lu.get("post_topic_depth") in ["discovery_friction", "complaining_keywords"]
                    is_hot_candidate = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or has_high_friction_topic)
                    
                    if is_hot_candidate:
                        try:
                            enriched = await enrich_company_waterfall(
                                person_url=lu.get("linkedin_url"),
                                million_verifier_enabled=million_verifier_enabled
                            )
                            if enriched:
                                async with SessionLocal() as session:
                                    async with session.begin():
                                        company_data_for_upsert = enriched.copy()
                                        person_email = company_data_for_upsert.pop("person_email", None)
                                        email_status = company_data_for_upsert.pop("email_verification_status", None)
                                        
                                        if person_email: lu["email"] = person_email
                                        if email_status: lu["email_verification_status"] = email_status
                                        
                                        profile_stmt = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == lu.get("linkedin_url"))
                                        db_profile = (await session.execute(profile_stmt)).scalar_one_or_none()
                                        
                                        update_vals = {}
                                        if db_profile:
                                            lu["id"] = str(db_profile.id)
                                            if person_email: db_profile.email = person_email
                                            if email_status: db_profile.email_verification_status = email_status
                                            
                                            if enriched.get("person_name"):
                                                db_profile.name = enriched["person_name"]
                                                lu["name"] = enriched["person_name"]
                                            if enriched.get("headline"):
                                                db_profile.headline = enriched["headline"]
                                                lu["headline"] = enriched["headline"]
                                            
                                            # Metadata sync
                                            try:
                                                current_meta = json.loads(db_profile.profile_metadata or "{}")
                                            except:
                                                current_meta = {}
                                            
                                            current_meta.update({
                                                "person_email": person_email,
                                                "is_enriched": True,
                                                "company_name": enriched.get("company_name")
                                            })
                                            db_profile.profile_metadata = json.dumps(current_meta)
                                            lu["profile_metadata"] = current_meta

                                        # Company Upsert
                                        if enriched.get("linkedin_url") or enriched.get("domain"):
                                            company = await upsert_company(
                                                session, company_data_for_upsert,
                                                linkedin_url=enriched.get("linkedin_url"),
                                                domain=enriched.get("domain")
                                            )
                                            lu["company_id"] = str(company.id)
                                            if db_profile: db_profile.company_id = company.id
                                            
                                        # Re-validation
                                        new_fit, new_reasoning = await revalidate_lead_fit_async(lu, enriched, icp_data)
                                        lu["is_fit"] = new_fit
                                        lu["fit_reasoning"] = new_reasoning
                                        if db_profile:
                                            db_profile.is_fit = new_fit
                                            db_profile.fit_reasoning = new_reasoning

                        except Exception as ee:
                            logger.error(f"Error enriching {lu.get('name')}: {ee}")
                            
                    # FINAL CLASSIFICATION for Slack
                    has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point"]
                    is_hot = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or (lu.get("post_topic_depth") in ["discovery_friction", "complaining_keywords"]))

                    if lu.get("is_fit"):
                        import hashlib
                        lead_url = lu.get("linkedin_url")
                        current_comment = (lu.get("comment") or "").strip()
                        raw_key = f"{lead_url}:{current_comment}"
                        idempotency_key = f"lead_interaction:{hashlib.md5(raw_key.encode()).hexdigest()}"

                        if is_hot: title_prefix = "🔥 Hot Lead"
                        elif lu.get("intent") == "hand_raiser": title_prefix = "🙋 Hand Raiser"
                        elif lu.get("intent") == "pain_point": title_prefix = "🚨 Pain Point"
                        else: title_prefix = "👀 Qualified Lead"

                        async with SessionLocal() as session:
                            await log_activity_and_notify(
                                session,
                                type="high_potential" if is_hot else "comment",
                                title=f"{title_prefix}: {lu.get('name') or 'Someone'} linked to {lu.get('competitor') or 'competitor'}",
                                description=f"Intent: {lu.get('intent')} | Sentiment: {lu.get('sentiment')}\nComment: {lu.get('comment')}",
                                metadata=lu,
                                user_id=user_id,
                                org_id=org_id,
                                idempotency_key=idempotency_key
                            )

                # Final broadcast: Merge company data into lu before broadcasting
                for lu in event_leads_batch:
                    # In case of enrichment, we might have updated lu with company_id, email, etc.
                    # We should also attach the company object if it exists
                    if lu.get("company_id"):
                        async with SessionLocal() as session:
                            comp_res = await session.execute(select(Company).where(Company.id == lu["company_id"]))
                            company = comp_res.scalar_one_or_none()
                            if company:
                                lu["company"] = {
                                    "id": str(company.id),
                                    "name": company.name,
                                    "website": company.website,
                                    "industries": company.industries,
                                    "employee_count": company.employee_count,
                                    "revenue_estimate": company.revenue,
                                    "market_cap": company.market_cap,
                                    "total_funding": company.total_funding,
                                    "headquarters": company.headquarters,
                                    "description": company.description
                                }

                # Broadcast batch update
                await event_manager.broadcast({
                    "type": "classification_update",
                    "leads": event_leads_batch
                }, org_id=org_id)
            else:
                 logger.debug(f"Batch {i//batch_size + 1} empty.")

    except Exception as e:
        logger.error(f"CRITICAL Error in classification: {e}", exc_info=True)
        await event_manager.broadcast({
            "type": "classification_error",
            "message": str(e)
        }, org_id=org_id)
