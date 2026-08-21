
import os
import logging
import json
import datetime
import uuid
from typing import List, Optional
from supabase import create_client, Client
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db.database import SessionLocal
from db.models import KnowledgeAsset, OrganizationSettings

logger = logging.getLogger(__name__)
load_dotenv()

class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        self.bucket_name = os.getenv("KNOWLEDGE_BUCKET") or (
            "trial" if os.getenv("ENVIRONMENT") == "trial" else "knowledge-base"
        )
        
        # Robust URL resolution
        if self.url and ("pooler.supabase.com" in self.url or not self.url.startswith("http")):
             if self.database_url and "postgres." in self.database_url:
                try:
                    part1 = self.database_url.split("postgres.")[1]
                    project_ref = part1.split(":")[0]
                    self.url = f"https://{project_ref}.supabase.co"
                except:
                    pass

        self.client: Client = None
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                # Ensure bucket exists
                try:
                    self.client.storage.get_bucket(self.bucket_name)
                except:
                    try:
                        self.client.storage.create_bucket(self.bucket_name, options={"public": False})
                    except:
                        pass
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}")

    def batch_upsert_profiles(self, profiles: list[dict]):
        """Batch upsert profiles using Supabase client."""
        if not self.client or not profiles:
            return []

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

        urls = list(batch_map.keys())
        response = self.client.table("identified_profiles").select("*").in_("linkedin_url", urls).execute()
        existing_profiles = {rp["linkedin_url"]: rp for rp in response.data}

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

        if upsert_data:
            result = self.client.table("identified_profiles").upsert(upsert_data).execute()
            return result.data
        
    def upload_file(self, bucket_name: str, storage_path: str, content: bytes, content_type: str = "text/markdown"):
        """Uploads a file to Supabase Storage."""
        if not self.client: return None
        try:
            res = self.client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            return res
        except Exception as e:
            logger.error(f"Error uploading to Supabase Storage: {e}")
            return None

    def delete_file(self, bucket_name: str, storage_path: str):
        """Deletes a file from Supabase Storage."""
        if not self.client: return False
        try:
            self.client.storage.from_(bucket_name).remove([storage_path])
            return True
        except Exception as e:
            logger.error(f"Error deleting from Supabase Storage: {e}")
            return False

    def download_file(self, bucket_name: str, storage_path: str):
        """Downloads a file from Supabase Storage."""
        if not self.client: return None
        try:
            return self.client.storage.from_(bucket_name).download(storage_path)
        except Exception as e:
            logger.error(f"Error downloading from Supabase Storage: {e}")
            return None

    async def get_knowledge_assets(self, org_id: str):
        """Fetches knowledge assets for an organization using SQLAlchemy."""
        try:
            async with SessionLocal() as session:
                org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
                stmt = select(KnowledgeAsset).where(KnowledgeAsset.organization_id == org_uuid).order_by(KnowledgeAsset.created_at.desc())
                result = await session.execute(stmt)
                assets = result.scalars().all()
                return [
                    {
                        "id": str(a.id),
                        "filename": a.filename,
                        "namespace": a.namespace,
                        "file_size": a.file_size,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                        "storage_path": a.storage_path,
                        "asset_metadata": json.loads(a.asset_metadata) if a.asset_metadata else {}
                    } for a in assets
                ]
        except Exception as e:
            logger.error(f"Error fetching knowledge assets: {e}")
            return []

    async def create_knowledge_asset(self, asset_data: dict):
        """Creates a knowledge asset record using SQLAlchemy."""
        try:
            async with SessionLocal() as session:
                asset = KnowledgeAsset(
                    organization_id=uuid.UUID(asset_data["organization_id"]) if isinstance(asset_data["organization_id"], str) else asset_data["organization_id"],
                    created_by_id=uuid.UUID(asset_data["created_by_id"]) if isinstance(asset_data["created_by_id"], str) else asset_data["created_by_id"],
                    filename=asset_data["filename"],
                    storage_path=asset_data["storage_path"],
                    namespace=asset_data["namespace"],
                    file_size=asset_data.get("file_size"),
                    asset_metadata=json.dumps(asset_data.get("asset_metadata", {}))
                )
                session.add(asset)
                await session.commit()
                await session.refresh(asset)
                return {
                    "id": str(asset.id),
                    "filename": asset.filename,
                    "namespace": asset.namespace,
                    "file_size": asset.file_size,
                    "storage_path": asset.storage_path
                }
        except Exception as e:
            logger.error(f"Error creating knowledge asset: {e}")
            return None

    async def update_knowledge_asset_metadata(self, asset_id: str, metadata: dict):
        """Updates asset_metadata for a specific asset."""
        try:
            async with SessionLocal() as session:
                asset_uuid = uuid.UUID(asset_id) if isinstance(asset_id, str) else asset_id
                stmt = update(KnowledgeAsset).where(KnowledgeAsset.id == asset_uuid).values(
                    asset_metadata=json.dumps(metadata)
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating knowledge asset metadata: {e}")
            return False

    async def delete_knowledge_asset(self, asset_id: str):
        """Deletes a knowledge asset record from the database."""
        try:
            async with SessionLocal() as session:
                asset_uuid = uuid.UUID(asset_id) if isinstance(asset_id, str) else asset_id
                stmt = delete(KnowledgeAsset).where(KnowledgeAsset.id == asset_uuid)
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting knowledge asset: {e}")
            return False

# Singleton instance
supabase_svc = SupabaseService()
