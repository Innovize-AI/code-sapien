from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
import logging
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import OrganizationSettings, Profile, KnowledgeAsset
from db.schemas import SellingProfileConfig, ProductConfig
from services.knowledge_service import KnowledgeService
from services.supabase_service import supabase_svc
from dependencies import get_current_user, require_admin



logger = logging.getLogger(__name__)

import time

router = APIRouter(tags=['Knowledge Base'])
# No global knowledge_service - must be resolved per-request

# --- Pinecone stats cache ---------------------------------------------------
# Pinecone describe_index_stats is a synchronous network call (~500ms-2s).
# Cache the result per index_name for 60 seconds.
_pinecone_stats_cache: dict[str, tuple[dict, float]] = {}
_PINECONE_STATS_TTL = 60  # seconds


def _get_cached_stats(index_name: str) -> dict | None:
    entry = _pinecone_stats_cache.get(index_name)
    if entry and (time.monotonic() - entry[1]) < _PINECONE_STATS_TTL:
        return entry[0]
    return None


def _set_cached_stats(index_name: str, stats: dict):
    _pinecone_stats_cache[index_name] = (stats, time.monotonic())
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    file_path: Optional[str] = None
    namespace: str
    content: Optional[str] = None
    metadata: Optional[dict] = None

class NamespaceInfo(BaseModel):
    name: str
    description: str
    count: int

@router.get("/namespaces", response_model=List[NamespaceInfo])
async def get_namespaces(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Returns a list of available namespaces in the Knowledge Base with real counts.
    """
    try:
        # Resolve the correct index for this organization
        from db.crud import get_org_settings
        settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
        
        trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
        index_name = settings.pinecone_index_name if settings and settings.pinecone_index_name else None
        
        if trial_mode and not index_name:
            # Strictly return 0s if no index is provisioned for this organization
            return [
                NamespaceInfo(name="playbooks", description="Strategic sales frameworks and messaging", count=0),
                NamespaceInfo(name="solutions", description="Technical product details and implementation guides", count=0),
                NamespaceInfo(name="case-studies", description="ROI proofs and success stories", count=0),
            ]
            
        index_name = index_name or "glial-index"

        # Use cached stats to avoid a blocking Pinecone network call on every request
        namespaces_stats = {}
        cached = _get_cached_stats(index_name)
        if cached is not None:
            namespaces_stats = cached.get("namespaces", {})
        else:
            try:
                ks = KnowledgeService(index_name=index_name)
                raw_stats = ks.get_index_stats()
                _set_cached_stats(index_name, raw_stats)
                namespaces_stats = raw_stats.get("namespaces", {})
            except Exception as pe:
                logger.warning(f"Pinecone stats unavailable, returning 0 counts: {pe}")
        
        # Mapping names to friendly descriptions
        namespace_meta = {
            "playbooks": "Strategic sales frameworks and messaging",
            "solutions": "Technical product details and implementation guides",
            "case-studies": "ROI proofs and success stories"
        }
        
        results = []
        for name, desc in namespace_meta.items():
            results.append(NamespaceInfo(
                name=name,
                description=desc,
                count=namespaces_stats.get(name, {}).get("vector_count", 0)
            ))
        return results
    except Exception as e:
        logger.error(f"Error fetching Pinecone stats: {e}")
        return [
            NamespaceInfo(name="playbooks", description="Strategic sales frameworks and messaging", count=0),
            NamespaceInfo(name="solutions", description="Technical product details and implementation guides", count=0),
            NamespaceInfo(name="case-studies", description="ROI proofs and success stories", count=0),
        ]

@router.get("/list-files")
async def list_knowledge_files(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Lists the knowledge assets from the database for the current organization.
    """
    from sqlalchemy import select as sa_select
    import uuid
    org_uuid = uuid.UUID(str(current_user.organization_id)) if current_user.organization_id else None
    
    assets_raw = []
    if org_uuid:
        stmt = sa_select(KnowledgeAsset).where(
            KnowledgeAsset.organization_id == org_uuid
        ).order_by(KnowledgeAsset.created_at.desc())
        result = await db.execute(stmt)
        assets_raw = result.scalars().all()
    
    files = [
        {
            "id": str(a.id),
            "name": a.filename,
            "namespace": a.namespace,
            "size": a.file_size,
            "modified": a.created_at.isoformat() if a.created_at else None,
            "storage_path": a.storage_path,
        }
        for a in assets_raw
    ]
    return {"files": files}

@router.post("/ingest")
async def ingest_file(
    request: IngestRequest, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Ingests a specific file into a namespace.
    """
    try:
        from db.crud import get_org_settings
        settings = await get_org_settings(db, admin_user.id, admin_user.organization_id)
        trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
        index_name = settings.pinecone_index_name if settings and settings.pinecone_index_name else None
        
        if trial_mode and not index_name:
             raise HTTPException(status_code=400, detail="Pinecone index not provisioned for this organization.")
             
        index_name = index_name or "glial-index"
        ks = KnowledgeService(index_name=index_name)

        if request.file_path:
            # Ensure path is absolute or relative to project root
            full_path = request.file_path
            if not os.path.isabs(full_path):
                full_path = os.path.join(os.getcwd(), full_path)
            
            # Normalize namespace
            namespace = request.namespace
            if namespace == "casestudies":
                namespace = "case-studies"
                
            # Ensure metadata exists
            ingest_metadata = request.metadata or {}
            if "source" not in ingest_metadata:
                ingest_metadata["source"] = f"org_{admin_user.organization_id}_{os.path.basename(full_path)}"
            if "organization_id" not in ingest_metadata:
                ingest_metadata["organization_id"] = str(admin_user.organization_id)

            result = await ks.ingest_markdown_file(
                full_path, 
                namespace, 
                ingest_metadata
            )
            return {"status": "success", "result": result}
        else:
            raise HTTPException(status_code=400, detail="Only file_path ingestion is currently supported.")
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-defaults")
async def sync_defaults(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin_user: Profile = Depends(require_admin)):
    """
    Syncs the project's global default playbooks to the organization's private space by prefixing them.
    """
    base_dir = os.path.join(os.getcwd(), "..", "market_validation", "innovize-ai")
    if not os.path.exists(base_dir):
        base_dir = "market_validation/innovize-ai"
        if not os.path.exists(base_dir):
            raise HTTPException(status_code=404, detail="Market validation directory not found")

    # Source files are those WITHOUT any org_ prefix
    source_files = [f for f in os.listdir(base_dir) if f.endswith(".md") and not f.startswith("org_")]
    org_prefix = f"org_{admin_user.organization_id}_"
    
    async def process_sync():
        for filename in source_files:
            source_path = os.path.join(base_dir, filename)
            target_filename = f"{org_prefix}{filename}"
            target_path = os.path.join(base_dir, target_filename)
            
            # Copy file to create a private prefixed version
            shutil.copy2(source_path, target_path)
            
            # Determine namespace
            namespace = "playbooks"
            if "case-study" in filename.lower():
                namespace = "case-studies"
            elif "one-pager" in filename.lower() or "offerings" in filename.lower():
                namespace = "solutions"
            
            try:
                from db.crud import get_org_settings
                settings = await get_org_settings(db, admin_user.id, admin_user.organization_id)
                
                trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
                index_name = settings.pinecone_index_name if settings and settings.pinecone_index_name else None
                
                if trial_mode and not index_name:
                    logger.error(f"Sync failed: Pinecone index not provisioned for organization {admin_user.organization_id}")
                    continue
                    
                index_name = index_name or "glial-index"
                ks = KnowledgeService(index_name=index_name)
                # Ingest the private copy
                await ks.ingest_markdown_file(target_path, namespace)
            except Exception as e:
                logger.error(f"Failed to ingest synced file {target_filename}: {e}")

    background_tasks.add_task(process_sync)
    return {"status": "sync_started", "files_queued": len(source_files)}

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    namespace: str = Form("playbooks"),
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Uploads a file to Supabase Storage and records it in the database.
    """
    if namespace == "casestudies":
        namespace = "case-studies"
        
    try:
        content = await file.read()
        file_size = len(content)
        
        # 1. Upload to Supabase Storage
        # 1. Upload to Supabase Storage
        org_id_str = str(admin_user.organization_id)
        # Use org_id as the folder name as requested
        storage_path = f"{org_id_str}/{file.filename}"
        
        storage_res = supabase_svc.upload_file(
            bucket_name=supabase_svc.bucket_name,
            storage_path=storage_path,
            content=content
        )
        
        if not storage_res:
            raise HTTPException(status_code=500, detail="Failed to upload to storage")

        # 2. Record in Database
        asset_data = {
            "organization_id": org_id_str,
            "created_by_id": str(admin_user.id),
            "filename": file.filename,
            "storage_path": storage_path,
            "namespace": namespace,
            "file_size": file_size
        }
        asset = await supabase_svc.create_knowledge_asset(asset_data)

        # 3. Ingest into Pinecone
        # Pass explicit 'source' metadata to match the multi-tenant retrieval convention
        ingest_metadata = {
            "source": f"org_{org_id_str}_{file.filename}",
            "organization_id": org_id_str
        }
        from db.crud import get_org_settings
        settings = await get_org_settings(db, admin_user.id, admin_user.organization_id)
        
        trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
        index_name = settings.pinecone_index_name if settings and settings.pinecone_index_name else None
        
        if trial_mode and not index_name:
            raise HTTPException(status_code=400, detail="Pinecone index not provisioned for this organization.")
            
        index_name = index_name or "glial-index"
        ks = KnowledgeService(index_name=index_name)
        
        # Temporary local save for ingestion (required by current KnowledgeService method)
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(content)
            
        try:
            result = await ks.ingest_markdown_file(temp_path, namespace, metadata=ingest_metadata)
            
            # 4. Update database with enriched metadata
            if result and "metadata" in result:
                enriched_metadata = result["metadata"]
                # Filter out system fields before saving to DB if desired, or keep all
                await supabase_svc.update_knowledge_asset_metadata(asset["id"], enriched_metadata)
                
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return {
            "status": "success", 
            "asset_id": asset["id"] if asset else None,
            "filename": file.filename,
            "result": result
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    admin_user: Profile = Depends(require_admin)
):
    """
    Cleans up a knowledge asset from the DB, Storage, and Pinecone.
    """
    try:
        # 1. Fetch asset details first
        assets = await supabase_svc.get_knowledge_assets(str(admin_user.organization_id))
        asset = next((a for a in assets if a["id"] == asset_id), None)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found.")
            
        # 2. Delete from Pinecone (Graceful)
        try:
            from services.knowledge_service import KnowledgeService
            ks = KnowledgeService() # Use default index from env
            source_metadata = f"org_{admin_user.organization_id}_{asset['filename']}"
            ks.delete_vectors(source_metadata)
        except Exception as ve:
            logger.error(f"Vector deletion failed for {asset_id} but proceeding: {ve}")
        
        # 3. Delete from Supabase Storage (Graceful)
        if asset.get("storage_path"):
            try:
                supabase_svc.delete_file(supabase_svc.bucket_name, asset["storage_path"])
            except Exception as se:
                logger.error(f"Storage deletion failed for {asset_id} but proceeding: {se}")
            
        # 4. Delete from Database (Required)
        success = await supabase_svc.delete_knowledge_asset(asset_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete from database.")
            
        return {"status": "success", "message": "Asset and associated vectors deleted."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fatal error during asset deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets/{asset_id}/content")
async def get_asset_content(
    asset_id: str,
    current_user: Profile = Depends(get_current_user)
):
    """
    Fetches the raw content of a knowledge asset from storage.
    """
    # 1. Fetch asset details
    assets = await supabase_svc.get_knowledge_assets(str(current_user.organization_id))
    asset = next((a for a in assets if a["id"] == asset_id), None)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
        
    if not asset.get("storage_path"):
        raise HTTPException(status_code=400, detail="Asset has no associated storage path.")
        
    # 2. Download from Storage
    content_bytes = supabase_svc.download_file(supabase_svc.bucket_name, asset["storage_path"])
    
    if not content_bytes:
        raise HTTPException(status_code=404, detail="File not found in storage.")
        
    return {
        "filename": asset["filename"],
        "content": content_bytes.decode("utf-8", errors="replace")
    }

class StrategyConfig(BaseModel):
    filename: Optional[str] = None # Optional now, used for context if single file click
    is_strategic_pivot: bool
    target_roles: List[str]
    target_industries: List[str] = []
    product_name: Optional[str] = None
    description: Optional[str] = None
    attached_playbooks: List[str] = []
    attached_case_studies: List[str] = []
    relevant_files: List[str] = []

@router.post("/configure-strategy")
async def configure_strategy(
    config: StrategyConfig, 
    db: AsyncSession = Depends(get_db),
    admin_user: Profile = Depends(require_admin)
):
    """
    Updates the organization settings with the 'Hero Product' configuration.
    """
    from db.crud import get_org_settings
    settings = await get_org_settings(db, user_id=str(admin_user.id), org_id=admin_user.organization_id)
    
    if not settings:
        settings = OrganizationSettings(
            owner_id=admin_user.id,
            organization_id=admin_user.organization_id
        )
        db.add(settings)
    
    # Load existing profile or create new
    current_profile = SellingProfileConfig()
    if settings.selling_profile_json:
        try:
            data = json.loads(settings.selling_profile_json)
            current_profile = SellingProfileConfig(**data)
        except:
            pass

    # Update or Add Product
    # Fallback to filename if product_name not provided (legacy behavior)
    p_name = config.product_name
    if not p_name and config.filename:
        p_name = config.filename.replace(".md", "").replace("-", " ").title()
    
    if not p_name:
        raise HTTPException(status_code=400, detail="Product name is required.")

    # 1. Reset other pivots if this one is set to True (assuming single hero product for now)
    if config.is_strategic_pivot:
        for p in current_profile.products:
            p.is_strategic_pivot = False

    # 2. Find and update product
    found = False
    for p in current_profile.products:
        # Match by name or if the context file matches (legacy)
        match_by_name = p.name == p_name
        match_by_file = config.filename and (p.rag_context == config.filename or config.filename in p.relevant_files)
        
        if match_by_name or match_by_file:
            p.name = p_name # Update name in case it changed
            if config.description:
                p.description = config.description
            p.is_strategic_pivot = config.is_strategic_pivot
            p.target_roles = config.target_roles
            p.target_industries = config.target_industries
            p.attached_playbooks = config.attached_playbooks
            p.attached_case_studies = config.attached_case_studies
            p.relevant_files = config.relevant_files
            
            # Legacy fields update
            if config.filename:
                 p.rag_context = config.filename

            # Ensure relevant files contains the filename if present
            if config.filename and config.filename not in p.relevant_files:
                p.relevant_files.append(config.filename)
            
            found = True
            break
    
    if not found:
        # Default relevant files to include the current filename if provided
        initial_files = config.relevant_files
        if flag_filename := config.filename:
            if flag_filename not in initial_files:
                initial_files.append(flag_filename)

        new_product = ProductConfig(
            name=p_name,
            description=config.description or "Strategic Product from Knowledge Base",
            is_strategic_pivot=config.is_strategic_pivot,
            target_roles=config.target_roles,
            attached_playbooks=config.attached_playbooks,
            attached_case_studies=config.attached_case_studies,
            relevant_files=initial_files,
            rag_context=config.filename
        )
        current_profile.products.append(new_product)
        
    settings.selling_profile_json = current_profile.json()
    await db.commit()
    
    return {"status": "success", "profile": current_profile.dict()}

@router.get("/strategy")
async def get_strategy(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Gets the current strategic pivot configuration.
    """
    from db.crud import get_org_settings
    settings = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
    
    if not settings or not settings.selling_profile_json:
        return {"products": []}
        
    return json.loads(settings.selling_profile_json)

