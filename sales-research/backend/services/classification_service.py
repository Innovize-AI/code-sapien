import asyncio
import json
from typing import List
from db.database import SessionLocal
from db import batch_upsert_identified_profiles
from agents.linkedin_agent import batch_classify_profiles_async
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
                    "headline": lead.get("headline", "")
                }
        
        unique_profiles_list = list(unique_profiles_map.values())
        if not unique_profiles_list:
            return

        # 2. Batch Classify & Update Iteratively
        batch_size = 100
        for i in range(0, len(unique_profiles_list), batch_size):
            batch = unique_profiles_list[i : i + batch_size]
            
            # A. Native Async AI Call
            batch_res = await batch_classify_profiles_async(batch)
            
            # B. Identify which leads to update from this batch
            batch_urls = set(item['id'] for item in batch)
            leads_to_update_batch = []
            event_leads_batch = []

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
                    if lu.get("is_fit") or lu.get("intent") == "pain_point":
                        async with SessionLocal() as session:
                            # We don't use session.begin() here because log_activity_and_notify handles its own commits via CRUD
                            await log_activity_and_notify(
                                session,
                                type="high_potential" if lu.get("is_fit") else "comment",
                                title=f"Hot Lead: {lu.get('name') or 'Someone'} linked to {lu.get('competitor') or 'competitor'}",
                                description=f"Intent: {lu.get('intent')} | Sentiment: {lu.get('sentiment')}\nComment: {lu.get('comment')}",
                                metadata=lu
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
