import asyncio
import json
from typing import List
from sqlalchemy import select
from db.database import SessionLocal
from db.models import IdentifiedProfile
from db import batch_upsert_identified_profiles
from utils.activity_helper import log_activity_and_notify

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
    try:
        print(f"DEBUG: Background Task Started for {len(raw_leads)} leads")
        
        # 1. Prepare unique profiles for batch classification
        unique_profiles_map = {}
        for lead in raw_leads:
            if lead["linkedin_url"] not in unique_profiles_map:
                unique_profiles_map[lead["linkedin_url"]] = {
                    "id": lead["linkedin_url"],
                    "headline": lead.get("headline", ""),
                    "comment": lead.get("comment", ""),
                    "source_post": lead.get("source_post", "")
                }
        
        unique_profiles_list = list(unique_profiles_map.values())
        if not unique_profiles_list:
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
        
        # Keep only profiles that are NOT in existing_urls
        new_profiles_list = [p for p in unique_profiles_list if p["id"] not in existing_urls]
        
        print(f"DEBUG: Found {len(existing_urls)} existing profiles. Processing {len(new_profiles_list)} new profiles for AI classification.")
        
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
            return

        # 2. Batch Classify & Update Iteratively
        batch_size = 100
        for i in range(0, len(new_profiles_list), batch_size):
            batch = new_profiles_list[i : i + batch_size]
            
            # A. Native Async AI Call
            from agents.linkedin_agent import batch_classify_profiles_async
            batch_res = await batch_classify_profiles_async(batch)
            
            # B. Identify which leads to update from this batch
            batch_urls = set(item['id'] for item in batch)
            leads_to_update_batch = []
            event_leads_batch = []

            # Include existing profile data in the first batch broadcast if available
            if i == 0 and existing_profile_data_map:
                event_leads_batch.extend(existing_profile_data_map.values())

            for lead in raw_leads:
                if lead["linkedin_url"] in batch_urls:
                    c = batch_res.get(lead["linkedin_url"])
                    if c:
                        updated_data = {
                            "linkedin_url": lead["linkedin_url"],
                            "is_fit": c.get("is_fit"),
                            "is_competitor": c.get("is_competitor"),
                            "is_decision_maker": c.get("is_decision_maker"),
                            "fit_reasoning": c.get("reasoning"),
                            "intent": c.get("intent"),
                            "post_topic_depth": c.get("post_topic_depth"),
                            "sentiment": c.get("sentiment"),
                            # Carry over metadata from raw lead
                            "name": lead.get("name"),
                            "comment": lead.get("comment"),
                            "source_post": lead.get("source_post"),
                            "source_post_url": lead.get("source_post_url"),
                            "competitor": lead.get("competitor")
                        }
                        leads_to_update_batch.append(updated_data)
                        event_leads_batch.append(updated_data)

            # C. Save & Broadcast this batch immediately
            if leads_to_update_batch:
                async with SessionLocal() as session:
                    async with session.begin():
                        await batch_upsert_identified_profiles(session, leads_to_update_batch)
                
                print(f"DEBUG: Batch {i//batch_size + 1} - Updated {len(leads_to_update_batch)} profiles")
                
                # D. Trigger Individual Notifications for Hot Leads or Pain Points
                for lu in leads_to_update_batch:
                    # High Priority: fit AND high intent OR just a pain point intent
                    is_hot = lu.get("is_fit") and lu.get("intent") in ["interested", "pain_point"]
                    is_qualified = lu.get("is_fit") and not is_hot
                    
                    if is_hot or lu.get("intent") == "pain_point" or is_qualified:
                        import hashlib
                        lead_url = lu.get("linkedin_url")
                        current_comment = (lu.get("comment") or "").strip()
                        
                        # Generate a unique key based on URL and Comment to prevent duplicate alerts
                        # Even if the worker retries, this key will be identical.
                        raw_key = f"{lead_url}:{current_comment}"
                        idempotency_key = f"lead_interaction:{hashlib.md5(raw_key.encode()).hexdigest()}"

                        title_prefix = "🔥 Hot Lead" if is_hot else "👀 Qualified Lead"
                        if lu.get("intent") == "pain_point":
                            title_prefix = "🚨 Pain Point"

                        async with SessionLocal() as session:
                            await log_activity_and_notify(
                                session,
                                type="high_potential" if is_hot else "comment",
                                title=f"{title_prefix}: {lu.get('name') or 'Someone'} linked to {lu.get('competitor') or 'competitor'}",
                                description=f"Intent: {lu.get('intent')} | Sentiment: {lu.get('sentiment')}\nComment: {lu.get('comment')}",
                                metadata=lu,
                                idempotency_key=idempotency_key
                            )
                
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
