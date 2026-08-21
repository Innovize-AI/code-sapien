import asyncio
import json
import logging
import os
import re
from typing import List, Optional
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


def _headcount_in_icp(employee_count: Optional[int], icp_data: Optional[dict]) -> bool:
    """
    Returns True if employee_count falls within any range defined in icp_data.company_size.
    Returns True (pass-through) when icp_data has no company_size or employee_count is unknown.
    """
    if not icp_data or not employee_count:
        return True  # can't filter without data — let Apollo decide via revalidation

    raw = icp_data.get("company_size")
    if not raw:
        return True

    sizes = raw if isinstance(raw, list) else [raw]
    for size in sizes:
        size = str(size).strip()
        if "+" in size:
            min_val = int(re.sub(r"[^\d]", "", size.split("+")[0]) or 0)
            if employee_count >= min_val:
                return True
        elif "-" in size:
            parts = re.split(r"[-–]", size)
            try:
                min_val = int(re.sub(r"[^\d]", "", parts[0]))
                max_val = int(re.sub(r"[^\d]", "", parts[1]))
                if min_val <= employee_count <= max_val:
                    return True
            except (ValueError, IndexError):
                continue
    return False

from db.database import SessionLocal
from db.models import IdentifiedProfile, OrganizationSettings, Company
from db.crud import batch_upsert_identified_profiles, upsert_company, get_active_icp
from utils.activity_helper import log_activity_and_notify
from agents.linkedin_agent import batch_classify_profiles_async, enrich_company_waterfall, get_company_details
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
                competitor_val = lead.get("competitor") or ""
                unique_profiles_map[n_url] = {
                    "id": n_url,
                    "headline": lead.get("headline", ""),
                    "comment": lead.get("comment", ""),
                    "source_post": lead.get("source_post", ""),
                    "name": lead.get("name"),
                    "source_post_url": lead.get("source_post_url"),
                    "competitor": competitor_val,
                    "discovery_source": "keyword" if str(competitor_val).startswith("Keyword:") else "other"
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
        digest_leads = []  # Accumulated across all batches for a single grouped Slack digest
        
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
                    raw_batch_res = await batch_classify_profiles_async(ai_sub_batch, company_context=company_context)
                    # Normalize LLM output URLs to ensure they match our internal IDs
                    for k, v in raw_batch_res.items():
                        norm_k = normalize_linkedin_url(k)
                        batch_res[norm_k] = v
            
            logger.info(f"batch res response: {batch_res}")
            leads_to_update_batch = []
            event_leads_batch = []
            
            for lead in batch:
                logger.info(f"Lead in batch: {lead}")
                lead_n_url = lead.get("id") or lead.get("linkedin_url")
                c = batch_res.get(lead_n_url)
                logger.info(f"Looking up URL in batch_res: '{lead_n_url}'. Found? {bool(c)}")
                
                if c:
                    logger.info(f"Classifying {lead_n_url}: Result type={type(c)}")
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
                    lead["linkedin_url"] = lead_n_url
                    leads_to_update_batch.append(lead)
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
                        profile_urls = [l.get("linkedin_url") or l.get("id") for l in event_leads_batch if l.get("linkedin_url") or l.get("id")]
                        id_res = await session.execute(
                            select(IdentifiedProfile.id, IdentifiedProfile.linkedin_url)
                            .where(IdentifiedProfile.linkedin_url.in_(profile_urls))
                        )
                        id_map = {r[1]: str(r[0]) for r in id_res.all()}
                        for lu in event_leads_batch:
                            url = lu.get("linkedin_url") or lu.get("id")
                            lu["linkedin_url"] = url
                            if url in id_map:
                                lu["id"] = id_map[url]
                
                # 2. Individual Enrichment & Notifications
                for lu in leads_to_update_batch:
                    if lu.get("is_strategic_seller"):
                        continue

                    has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point", "demo_interest"]
                    has_high_friction_topic = lu.get("post_topic_depth") in ["discovery_friction", "complaining_keywords"]
                    is_hot_candidate = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or has_high_friction_topic)
                    is_slack_candidate = lu.get("is_fit") and lu.get("is_decision_maker")

                    if is_hot_candidate:
                        # Full enrichment: Apollo People Match → email + company data + ICP revalidation
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

                                        if enriched.get("linkedin_url") or enriched.get("domain"):
                                            company = await upsert_company(
                                                session, company_data_for_upsert,
                                                linkedin_url=enriched.get("linkedin_url"),
                                                domain=enriched.get("domain")
                                            )
                                            lu["company_id"] = str(company.id)
                                            if db_profile: db_profile.company_id = company.id

                                        new_fit, new_reasoning = await revalidate_lead_fit_async(lu, enriched, icp_data)
                                        lu["is_fit"] = new_fit
                                        lu["fit_reasoning"] = new_reasoning
                                        if db_profile:
                                            db_profile.is_fit = new_fit
                                            db_profile.fit_reasoning = new_reasoning

                        except Exception as ee:
                            logger.error(f"Error in hot enrichment for {lu.get('name')}: {ee}")

                    elif is_slack_candidate:
                        # Lightweight headcount-only path: LinkedIn RapidAPI → Apollo fallback → ICP revalidation
                        try:
                            employee_count = lu.get("employee_count")
                            company_linkedin_url = lu.get("company_linkedin_url")

                            # 1. Try LinkedIn company page (no Apollo credit)
                            if not employee_count and company_linkedin_url:
                                identifier = company_linkedin_url.rstrip("/").split("/")[-1]
                                company_res = await asyncio.to_thread(get_company_details, identifier)
                                if company_res:
                                    employee_count = (company_res.get("stats") or {}).get("employee_count")
                                if employee_count:
                                    lu["employee_count"] = employee_count
                                    logger.info(f"Headcount resolved via LinkedIn for {lu.get('name')}: {employee_count}")

                            # 2. Apollo — only run if headcount passes ICP or is still unknown
                            fallback_email = None
                            fallback_email_status = None
                            headcount_known = employee_count is not None
                            headcount_passes_icp = _headcount_in_icp(employee_count, icp_data)

                            if not headcount_known or headcount_passes_icp:
                                # headcount unknown → Apollo is last resort for both headcount + email
                                # headcount passes ICP → Apollo only for email (cheap, already paying)
                                fallback = await enrich_company_waterfall(
                                    person_url=lu.get("linkedin_url"),
                                    million_verifier_enabled=million_verifier_enabled
                                )
                                if fallback:
                                    if not employee_count:
                                        employee_count = fallback.get("employee_count")
                                        if employee_count:
                                            lu["employee_count"] = employee_count
                                    if fallback.get("company_name"):
                                        lu["company_name"] = fallback["company_name"]
                                    if fallback.get("industries"):
                                        lu["company_industries"] = fallback["industries"]
                                    fallback_email = fallback.get("person_email")
                                    fallback_email_status = fallback.get("email_verification_status")
                                    if fallback_email:
                                        lu["email"] = fallback_email
                                    if fallback_email_status:
                                        lu["email_verification_status"] = fallback_email_status
                            else:
                                logger.info(f"Skipping Apollo for {lu.get('name')} — headcount {employee_count} outside ICP range")

                            # 3. ICP revalidation + persist email if resolved
                            company_metrics = {"employee_count": lu.get("employee_count"), "industries": lu.get("company_industries")}
                            async with SessionLocal() as session:
                                async with session.begin():
                                    profile_stmt = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == lu.get("linkedin_url"))
                                    db_profile = (await session.execute(profile_stmt)).scalar_one_or_none()
                                    new_fit, new_reasoning = await revalidate_lead_fit_async(lu, company_metrics, icp_data)
                                    lu["is_fit"] = new_fit
                                    lu["fit_reasoning"] = new_reasoning
                                    if db_profile:
                                        db_profile.is_fit = new_fit
                                        db_profile.fit_reasoning = new_reasoning
                                        if fallback_email:
                                            db_profile.email = fallback_email
                                        if fallback_email_status:
                                            db_profile.email_verification_status = fallback_email_status

                        except Exception as ee:
                            logger.error(f"Error in headcount check for {lu.get('name')}: {ee}")
                            
                    # FINAL CLASSIFICATION for Slack
                    import hashlib
                    has_high_intent = lu.get("intent") in ["prospect_pain", "pain_point"]
                    is_hot = lu.get("is_fit") and lu.get("is_decision_maker") and (lu.get("is_buy_signal") or has_high_intent or (lu.get("post_topic_depth") in ["discovery_friction", "complaining_keywords"]))

                    if lu.get("is_fit") and lu.get("is_decision_maker"):
                        lead_url = lu.get("linkedin_url")
                        current_comment = (lu.get("comment") or "").strip()
                        idempotency_key = f"lead_interaction:{hashlib.md5(f'{lead_url}:{current_comment}'.encode()).hexdigest()}"

                        competitor_val = lu.get("competitor") or ""
                        is_keyword_lead = str(competitor_val).startswith("Keyword:")

                        if is_hot:
                            title_prefix = "🔥 Hot Lead"
                        elif lu.get("intent") == "hand_raiser":
                            title_prefix = "🙋 Hand Raiser"
                        elif lu.get("intent") in ("pain_point", "prospect_pain"):
                            title_prefix = "🚨 Pain Point"
                        else:
                            title_prefix = "👀 Qualified Lead"

                        # Build a human-readable signal reason for the Slack notification
                        if is_hot:
                            if lu.get("is_buy_signal"):
                                signal_reason = "Explicit buying signal detected in their comment"
                            elif lu.get("intent") in ("prospect_pain", "pain_point"):
                                signal_reason = "Expressed genuine frustration with current tools or process"
                            elif lu.get("post_topic_depth") == "discovery_friction":
                                signal_reason = "Mentioned struggle with lead discovery or data quality"
                            elif lu.get("post_topic_depth") == "complaining_keywords":
                                signal_reason = "Complained about specific industry tools or keywords"
                            else:
                                signal_reason = "Strong ICP match with high-intent signals"
                        elif lu.get("intent") == "hand_raiser":
                            signal_reason = "Explicitly asked for more information or a demo"
                        elif lu.get("intent") in ("pain_point", "prospect_pain"):
                            signal_reason = "Expressed pain with current solution or process"
                        elif lu.get("intent") == "passive_expert":
                            signal_reason = "Sharing relevant expertise — authority signal"
                        else:
                            signal_reason = "Decision maker at ICP company — no active signal yet"

                        # Build title context based on discovery source
                        if is_keyword_lead:
                            keyword = competitor_val.replace("Keyword:", "").strip()
                            title_context = f"found via keyword '{keyword}'"
                        elif competitor_val == "Apollo":
                            title_context = "found via Apollo Discovery"
                        elif competitor_val == "LinkedIn Jobs":
                            title_context = "found via LinkedIn Jobs"
                        elif competitor_val:
                            title_context = f"spotted on {competitor_val}"
                        else:
                            title_context = "discovered"

                        lu["signal_reason"] = signal_reason
                        lu["discovery_source"] = "keyword" if is_keyword_lead else "other"

                        # Determine tier for the digest grouping
                        if is_hot:
                            lead_tier = "hot"
                        elif lu.get("intent") == "hand_raiser":
                            lead_tier = "hand_raiser"
                        elif lu.get("intent") in ("pain_point", "prospect_pain"):
                            lead_tier = "pain_point"
                        else:
                            lead_tier = "qualified"

                        digest_leads.append({
                            "tier":                      lead_tier,
                            "name":                      lu.get("name"),
                            "headline":                  lu.get("headline"),
                            "linkedin_url":              lu.get("linkedin_url"),
                            "email":                     lu.get("email"),
                            "email_verification_status": lu.get("email_verification_status"),
                            "company_name":              lu.get("company_name"),
                            "employee_count":            lu.get("employee_count"),
                            "company_industries":        lu.get("company_industries"),
                            "intent":                    lu.get("intent"),
                            "sentiment":                 lu.get("sentiment"),
                            "competitor":                lu.get("competitor"),
                            "signal_reason":             signal_reason,
                            "post_link":                 lu.get("source_post_url"),
                            "comment":                   lu.get("comment"),
                            "reasoning":                 lu.get("fit_reasoning"),
                            "is_buy_signal":             lu.get("is_buy_signal", False),
                            "post_topic_depth":          lu.get("post_topic_depth"),
                        })

                        async with SessionLocal() as session:
                            await log_activity_and_notify(
                                session,
                                type="high_potential" if is_hot else "comment",
                                title=f"{title_prefix}: {lu.get('name') or 'Someone'} {title_context}",
                                description=f"Intent: {lu.get('intent')} | Sentiment: {lu.get('sentiment')}\nComment: {lu.get('comment')}",
                                metadata=lu,
                                user_id=user_id,
                                org_id=org_id,
                                idempotency_key=idempotency_key,
                                send_slack=False,  # Slack sent as grouped digest after all batches
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

        # ── Send grouped Slack digest for all leads that qualified this run ──────
        if digest_leads:
            try:
                from db.crud import get_org_settings
                from db.models import Profile
                from utils.slack_block_builder import build_lead_digest_blocks
                from utils.slack import send_slack_notification

                async with SessionLocal() as session:
                    settings = await get_org_settings(session, user_id=user_id, org_id=org_id)
                    if settings and settings.slack_webhook_url:
                        slack_enabled = True
                        if settings.integrations_config:
                            try:
                                cfg = json.loads(settings.integrations_config)
                                if cfg.get("slack") and not cfg["slack"].get("enabled", True):
                                    slack_enabled = False
                            except Exception:
                                pass

                        if slack_enabled:
                            rep_name = None
                            if user_id:
                                result = await session.execute(select(Profile).where(Profile.id == user_id))
                                profile = result.scalars().first()
                                if profile:
                                    rep_name = profile.email.split("@")[0].replace(".", " ").title()

                            # Derive source label from the leads themselves
                            keywords = {
                                l["competitor"].replace("Keyword:", "").strip()
                                for l in digest_leads
                                if str(l.get("competitor", "")).startswith("Keyword:")
                            }
                            competitor_names = {
                                l["competitor"] for l in digest_leads
                                if l.get("competitor") and not str(l["competitor"]).startswith("Keyword:")
                                and l["competitor"] not in ("Apollo", "LinkedIn Jobs")
                            }
                            if keywords and not competitor_names:
                                source_label = f"'{', '.join(sorted(keywords))}'"
                            elif competitor_names and not keywords:
                                source_label = f"Competitor: {', '.join(sorted(competitor_names))}"
                            else:
                                source_label = None

                            blocks = build_lead_digest_blocks(
                                digest_leads, rep_name=rep_name, source_label=source_label
                            )
                            total = len(digest_leads)
                            hot_count = sum(1 for l in digest_leads if l["tier"] == "hot")
                            fallback = (
                                f"📋 {total} lead{'s' if total > 1 else ''} qualified"
                                + (f" ({hot_count} hot)" if hot_count else "")
                            )
                            await send_slack_notification(settings.slack_webhook_url, fallback, blocks=blocks)
                            logger.info(f"Digest sent: {total} leads ({hot_count} hot) to Slack")
            except Exception as digest_err:
                logger.error(f"Error sending digest to Slack: {digest_err}", exc_info=True)

    except Exception as e:
        logger.error(f"CRITICAL Error in classification: {e}", exc_info=True)
        await event_manager.broadcast({
            "type": "classification_error",
            "message": str(e)
        }, org_id=org_id)

async def enrich_linkedin_job_leads_task(
    jobs: List[dict],
    user_id: str,
    org_id: str,
    apollo_api_key: str | None = None
):
    """
    Background worker for LinkedIn Job lead discovery.
    1. Groups jobs by company name.
    2. Runs enrich_job_leads_background_pipeline to resolve domains and batch-query Apollo for decision-makers.
    3. Triggers run_classification_and_update on the decision-maker profiles.
    4. Deletes the temporary starter company cards from the DB.
    """
    try:
        logger.info(f"Background Job Enrichment Task started for {len(jobs)} jobs.")
        
        # 1. Group jobs by company name
        grouped_jobs = {}
        for job in jobs:
            cname = job.get("company_name")
            if cname and cname != "Target Company":
                if cname not in grouped_jobs:
                    grouped_jobs[cname] = []
                grouped_jobs[cname].append(job)
                
        if not grouped_jobs:
            logger.info("No valid companies found in jobs list for background enrichment.")
            return

        # 2. Run Apollo and domain-resolution background pipeline
        from agents.linkedin_agent import enrich_job_leads_background_pipeline
        decision_maker_leads = await enrich_job_leads_background_pipeline(
            grouped_jobs=grouped_jobs,
            apollo_api_key=apollo_api_key,
            user_id=user_id,
            org_id=org_id
        )
        
        if not decision_maker_leads:
            logger.info("No decision makers found for hiring companies.")
            return
            
        logger.info(f"Found {len(decision_maker_leads)} decision-maker leads. Triggering immediate waterfall enrichment.")
        
        # 3. Trigger full Apollo enrichment via our existing pipeline
        to_enrich_ids = [l.get("profile_metadata", {}).get("apollo_id") for l in decision_maker_leads if l.get("profile_metadata", {}).get("apollo_id")]
        
        if to_enrich_ids:
            from routes.lead_discovery import enrich_and_save_leads
            async with SessionLocal() as db_session:
                await enrich_and_save_leads(
                    db=db_session,
                    person_ids=to_enrich_ids,
                    user_id=user_id,
                    org_id=org_id,
                    source_post=f"Hiring: {jobs[0].get('title')}" if jobs else "LinkedIn Job Discovery",
                    competitor="LinkedIn Jobs"
                )
        
        # 4. Clean up temporary starter company cards from the database
        company_urls = [job.get("company_url") for job in jobs if job.get("company_url")]
        company_names = [job.get("company_name") for job in jobs if job.get("company_name")]
        
        from sqlalchemy import delete, or_
        async with SessionLocal() as db:
            async with db.begin():
                # Delete starter company profiles where lead_source is 'linkedin_job' and website is empty (starter cards have website = "")
                stmt = delete(IdentifiedProfile).where(
                    IdentifiedProfile.lead_source == "linkedin_job",
                    IdentifiedProfile.website == "",
                    IdentifiedProfile.is_fit == False,
                    IdentifiedProfile.is_decision_maker == False
                )
                
                # Match the specific names/urls of companies we processed
                conditions = []
                if company_urls:
                    conditions.append(IdentifiedProfile.linkedin_url.in_(company_urls))
                if company_names:
                    conditions.append(IdentifiedProfile.name.in_(company_names))
                    
                if conditions:
                    stmt = stmt.where(or_(*conditions))
                    res = await db.execute(stmt)
                    logger.info(f"Cleaned up temporary starter company cards from the database: {res.rowcount} rows deleted.")
                    
    except Exception as e:
        logger.error(f"Error in enrich_linkedin_job_leads_task background worker: {e}", exc_info=True)
