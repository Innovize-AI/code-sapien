
import os
import json
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.client: Client = None
        if self.url and self.key:
            self.client = create_client(self.url, self.key)

    def batch_upsert_profiles(self, profiles: list[dict]):
        """
        Batch upsert profiles using Supabase client.
        profiles: list of {linkedin_url, name, comment, source_post, source_post_url, competitor}
        """
        if not self.client or not profiles:
            print("Supabase client not initialized or no profiles provided")
            return []

        # 1. Aggregate incoming batch in memory
        batch_map = {}
        for p in profiles:
            url = p.get("linkedin_url")
            if not url: continue
            
            if url not in batch_map:
                batch_map[url] = {
                    "linkedin_url": url,
                    "name": p.get("name"),
                    "comments": [p.get("comment")] if p.get("comment") else [],
                    "sources": []
                }
            
            source_urls = p.get("source_post_url", "").split(",") if p.get("source_post_url") else []
            for s_url in source_urls:
                if s_url and not any(s["url"] == s_url for s in batch_map[url]["sources"]):
                    batch_map[url]["sources"].append({
                        "title": p.get("source_post"),
                        "url": s_url,
                        "competitor": p.get("competitor")
                    })
            
            if p.get("comment") and p.get("comment") not in batch_map[url]["comments"]:
                batch_map[url]["comments"].append(p.get("comment"))

        # 2. Fetch all existing records in one shot
        urls = list(batch_map.keys())
        response = self.client.table("identified_profiles").select("*").in_("linkedin_url", urls).execute()
        existing_profiles = {rp["linkedin_url"]: rp for rp in response.data}

        # 3. Merge data
        upsert_data = []
        for url, data in batch_map.items():
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            if url in existing_profiles:
                existing = existing_profiles[url]
                
                try:
                    db_comments = json.loads(existing.get("comment_history") or "[]")
                except:
                    db_comments = []
                for c in data["comments"]:
                    if c not in db_comments: db_comments.append(c)
                
                try:
                    db_sources = json.loads(existing.get("source_posts") or "[]")
                except:
                    db_sources = []
                for s in data["sources"]:
                    if not any(ds["url"] == s["url"] for ds in db_sources):
                        db_sources.append(s)
                
                upsert_data.append({
                    "id": existing["id"],
                    "linkedin_url": url,
                    "name": data["name"] or existing.get("name"),
                    "comment_history": json.dumps(db_comments),
                    "source_posts": json.dumps(db_sources),
                    "last_interaction_at": now
                })
            else:
                upsert_data.append({
                    "linkedin_url": url,
                    "name": data["name"],
                    "comment_history": json.dumps(data["comments"]),
                    "source_posts": json.dumps(data["sources"]),
                    "last_interaction_at": now
                })

        # 4. Final Batch Upsert
        if upsert_data:
            result = self.client.table("identified_profiles").upsert(upsert_data).execute()
            return result.data
        
        return []

# Singleton instance
supabase_svc = SupabaseService()
