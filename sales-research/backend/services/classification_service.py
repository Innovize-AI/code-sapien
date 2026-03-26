import asyncio
import json
from typing import List
from sqlalchemy import select, update
from db.database import SessionLocal
from db.models import IdentifiedProfile
from db.crud import batch_upsert_identified_profiles, upsert_company, get_active_icp
from utils.activity_helper import log_activity_and_notify
from agents.linkedin_agent import batch_classify_profiles_async, enrich_company_waterfall
from agents.lead_scoring_agent import revalidate_lead_fit_async

class EventStreamManager:
    def __init__(self):
        self.active_connections: List[asyncio.Queue] = []

    async def subscribe(self):
        queue = asyncio.Queue()
        self.active_connections.append(queue)
        print(f"DEBUG: New SSE subscriber. Total: {len(self.active_connections)}")
        return queue

    async def unsubscribe(self, queue):
        if queue in self.active_connections:
            self.active_connections.remove(queue)
            print(f"DEBUG: SSE subscriber disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        if not self.active_connections:
            return
        
        payload = json.dumps(data)
        event = f"data: {payload}\n\n"
        
        for queue in self.active_connections:
            await queue.put(event)

event_manager = EventStreamManager()

async def run_classification_and_update(raw_leads: List[dict]):
    """
    Background task to classify leads and update DB.
    """
    from utils.url_normalize import normalize_linkedin_url
    
    try:
        print(f"DEBUG: Background Task Started for {len(raw_leads)} leads")
        
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
        
        print(f"DEBUG: Unique profiles to classify: {list(unique_profiles_map.keys())}")
        
        unique_profiles_list = list(unique_profiles_map.values())
        if not unique_profiles_list:
            print("DEBUG: No unique profiles found. Returning.")
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
        
        print(f"DEBUG: Found {len(existing_urls)} profiles with existing classification: {existing_urls}")
        
        # Keep only profiles that are NOT in existing_urls (using normalized comparison)
        new_profiles_list = [p for p in unique_profiles_list if p["id"] not in existing_urls]
        
        print(f"DEBUG: Processing {len(new_profiles_list)} new profiles for AI classification: {[p['id'] for p in new_profiles_list]}")
        
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
                        "is_fit": p.is_fit,
                        "is_competitor": p.is_competitor,
                        "is_decision_maker": p.is_decision_maker,
                        "fit_reasoning": p.fit_reasoning,
                        "intent": p.intent,
                        "sentiment": p.sentiment,
                        "name": p.name,
                        "headline": p.headline
                    }

        # If there are NO new profiles but there are existing ones, broadcast them now
        if not new_profiles_list and existing_profile_data_map:
            print("DEBUG: All discovered profiles already exist in DB. Broadcasting existing data.")
            await event_manager.broadcast({
                "type": "classification_update",
                "leads": list(existing_profile_data_map.values())
            })
            return
        
        if not new_profiles_list:
            print("DEBUG: No new profiles to classify. Returning.")
            return

        # 2. Batch Classify & Update Iteratively
        batch_size = 100
        for i in range(0, len(new_profiles_list), batch_size):
            batch = new_profiles_list[i : i + batch_size]
            print(f"DEBUG: Triggering AI for batch {i//batch_size + 1} ({len(batch)} profiles)...")
            
            # A. Native Async AI Call
            batch_res = await batch_classify_profiles_async(batch)
            print(f"DEBUG: AI returned {len(batch_res)} results: {list(batch_res.keys())}")
            
            # B. Identify which leads to update from this batch
            batch_urls = set(item['id'] for item in batch)
            leads_to_update_batch = []
            event_leads_batch = []

            # Include existing profile data in the first batch broadcast if available
            if i == 0 and existing_profile_data_map:
                event_leads_batch.extend(existing_profile_data_map.values())

            for lead in raw_leads:
                lead_n_url = normalize_linkedin_url(lead["linkedin_url"])
                print(f"DEBUG: Checking lead {lead_n_url} against batch_urls...")
                if lead_n_url in batch_urls:
                    print(f"DEBUG: Found lead {lead_n_url} in batch. Fetching AI result...")
                    c = batch_res.get(lead_n_url)
                    if c:
                        print(f"DEBUG: Applying AI result for {lead_n_url}: fit={c.get('is_fit')}")
                        updated_data = {
                            "linkedin_url": lead_n_url,
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
                            "comment": lead.get("comment"),
                            "source_post": lead.get("source_post"),
                            "source_post_url": lead.get("source_post_url"),
                            "competitor": lead.get("competitor")
                        }
                        leads_to_update_batch.append(updated_data)
                        event_leads_batch.append(updated_data)

            # C/D. Save, Enrich & Notify
            if leads_to_update_batch:
                async with SessionLocal() as session:
                    # 1. Batch Upsert Profiles
                    async with session.begin():
                        # Fetch ICP once per batch for efficiency
                        icp_data = await get_active_icp(session)
                        await batch_upsert_identified_profiles(session, leads_to_update_batch)
                    
                    print(f"DEBUG: Batch {i//batch_size + 1} - Updated {len(leads_to_update_batch)} profiles")
                    
                    # 2. Individual Enrichment & Notifications
                    for lu in leads_to_update_batch:
                        if lu.get("is_strategic_seller"):
                            print(f"DEBUG: Skipping notification for Strategic Seller {lu.get('name')}")
                            continue

                        is_hot = lu.get("is_fit") and (lu.get("is_buy_signal") or lu.get("intent") in ["hand_raiser", "prospect_pain", "interested", "pain_point"])
                        is_qualified = lu.get("is_fit") and not lu.get("is_buy_signal") and not lu.get("is_strategic_seller")
                        
                        if is_hot or lu.get("intent") in ["prospect_pain", "pain_point"] or is_qualified:
                            # Apollo Enrichment
                            try:
                                print(f"DEBUG: Enriching high-priority lead {lu.get('name')} via Apollo...")
                                enriched = await enrich_company_waterfall(person_url=lu.get("linkedin_url"))
                                if enriched:
                                    async with session.begin(): # Sub-transaction for company enrichment
                                        # Create a mutable copy for upsert_company and extract person_email
                                        company_data_for_upsert = enriched.copy()
                                        person_email = company_data_for_upsert.pop("person_email", None)
                                        
                                        # Enrich the lead with personal email if found
                                        if person_email:
                                            lu["email"] = person_email
                                        
                                        company = await upsert_company(
                                            session, 
                                            company_data_for_upsert, 
                                            linkedin_url=enriched.get("linkedin_url"),
                                            domain=enriched.get("domain")
                                        )
                                        lu.update({
                                            "company_id": str(company.id),
                                            "company_name": enriched.get("name"),
                                            "company_description": enriched.get("description"),
                                            "company_industries": enriched.get("industries"),
                                            "employee_count": enriched.get("employee_count"),
                                            "revenue": enriched.get("revenue")
                                        })
                                        update_vals = {"company_id": company.id}
                                        if person_email:
                                            update_vals["email"] = person_email
                                            
                                        # 4. RE-VALIDATE Fit with confirmed firmographics (using actual ICP)
                                        try:
                                            new_fit, new_reasoning = await revalidate_lead_fit_async(lu, enriched, icp_data)
                                            update_vals["is_fit"] = new_fit
                                            update_vals["fit_reasoning"] = new_reasoning
                                            # Update in-memory for broadcast
                                            lu["is_fit"] = new_fit
                                            lu["fit_reasoning"] = new_reasoning
                                        except Exception as re_e:
                                            print(f"Error re-validating lead {lu.get('name')}: {re_e}")
                                            
                                        await session.execute(
                                            update(IdentifiedProfile)
                                            .where(IdentifiedProfile.linkedin_url == lu.get("linkedin_url"))
                                            .values(**update_vals)
                                        )
                            except Exception as ee:
                                print(f"Error enriching lead {lu.get('name')}: {ee}")
                                
                            is_hot = lu.get("is_fit") and (lu.get("is_buy_signal") or lu.get("intent") in ["hand_raiser", "prospect_pain", "interested", "pain_point"])

                            import hashlib
                            import os
                            
                            # Slack Notification (Only if fit after re-evaluation)
                            if lu.get("is_fit"):
                                lead_url = lu.get("linkedin_url")
                                current_comment = (lu.get("comment") or "").strip()
                                raw_key = f"{lead_url}:{current_comment}"
                                idempotency_key = f"lead_interaction:{hashlib.md5(raw_key.encode()).hexdigest()}"

                                title_prefix = "🔥 Hot Lead" if is_hot else "👀 Qualified Lead"
                                if lu.get("intent") == "pain_point":
                                    title_prefix = "🚨 Pain Point"

                                # Use the same session for logging
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
                print(f"DEBUG: Broadcasted batch update for {len(event_leads_batch)} leads")
            else:
                 print(f"DEBUG: Batch {i//batch_size + 1} returned no results to update.")

    except Exception as e:
        print(f"CRITICAL Error in background classification: {e}")
        import traceback
        traceback.print_exc()
