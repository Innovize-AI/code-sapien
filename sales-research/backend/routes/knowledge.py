from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import OrganizationSettings, Profile
from db.schemas import SellingProfileConfig, ProductConfig
from services.knowledge_service import KnowledgeService
from dependencies import get_current_user, require_admin


router = APIRouter(tags=['Knowledge Base'])
knowledge_service = KnowledgeService(index_name="glial-index")

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
async def get_namespaces(current_user: Profile = Depends(get_current_user)):
    """
    Returns a list of available namespaces in the Knowledge Base with real counts.
    """
    try:
        stats = knowledge_service.get_index_stats()
        namespaces_stats = stats.get("namespaces", {})
        
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
        print(f"Error fetching Pinecone stats: {e}")
        # Fallback to zeros if Pinecone is not reachable
        return [
            NamespaceInfo(name="playbooks", description="Strategic sales frameworks and messaging", count=0),
            NamespaceInfo(name="solutions", description="Technical product details and implementation guides", count=0),
            NamespaceInfo(name="case-studies", description="ROI proofs and success stories", count=0),
        ]

@router.get("/list-files")
async def list_knowledge_files(current_user: Profile = Depends(get_current_user)):
    """
    Lists the files available in the market_validation directory.
    """
    # Assuming server runs from backend/ directory
    base_dir = os.path.join(os.getcwd(), "..", "market_validation", "innovize-ai")
    if not os.path.exists(base_dir):
        # Fallback if running from root
        base_dir = "market_validation/innovize-ai"
        if not os.path.exists(base_dir):
            return {"files": []}
    
    files = []
    for filename in os.listdir(base_dir):
        if filename.endswith(".md"):
            path = os.path.join(base_dir, filename)
            # Return path relative to project root for ingestion consistency
            rel_path = os.path.relpath(path, os.path.join(os.getcwd(), "..") if "backend" in os.getcwd() else os.getcwd())
            stats = os.stat(path)
            files.append({
                "name": filename,
                "path": rel_path,
                "size": stats.st_size,
                "modified": stats.st_mtime
            })
    return {"files": files}

@router.post("/ingest")
async def ingest_file(request: IngestRequest, admin_user: Profile = Depends(require_admin)):
    """
    Ingests a specific file into a namespace.
    """
    try:
        if request.file_path:
            # Ensure path is absolute or relative to project root
            full_path = request.file_path
            if not os.path.isabs(full_path):
                full_path = os.path.join(os.getcwd(), full_path)
            
            result = await knowledge_service.ingest_markdown_file(
                full_path, 
                request.namespace, 
                request.metadata
            )
            return {"status": "success", "result": result}
        else:
            raise HTTPException(status_code=400, detail="Only file_path ingestion is currently supported.")
    except Exception as e:
        print(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-defaults")
async def sync_defaults(background_tasks: BackgroundTasks, admin_user: Profile = Depends(require_admin)):
    """
    Auto-ingests the project's default playbooks into the knowledge base.
    """
    base_dir = os.path.join(os.getcwd(), "..", "market_validation", "innovize-ai")
    if not os.path.exists(base_dir):
        # Fallback if running from root
        base_dir = "market_validation/innovize-ai"
        if not os.path.exists(base_dir):
            raise HTTPException(status_code=404, detail="Market validation directory not found")

    files = [f for f in os.listdir(base_dir) if f.endswith(".md")]
    
    async def process_sync():
        for filename in files:
            path = os.path.join(base_dir, filename)
            # Route to namespaces based on filename
            namespace = "playbooks"
            if "case-study" in filename.lower():
                namespace = "case-studies"
            elif "one-pager" in filename.lower() or "offerings" in filename.lower():
                namespace = "solutions"
            
            try:
                await knowledge_service.ingest_markdown_file(path, namespace)
            except Exception as e:
                print(f"Failed to ingest {filename}: {e}")

    background_tasks.add_task(process_sync)
    return {"status": "sync_started", "files_queued": len(files)}

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    namespace: str = "playbooks",
    admin_user: Profile = Depends(require_admin)
):
    """
    Uploads a file to the market_validation directory and ingests it.
    """
    try:
        # 1. Save File
        base_dir = os.path.join(os.getcwd(), "..", "market_validation", "innovize-ai")
        if not os.path.exists(base_dir):
            base_dir = "market_validation/innovize-ai"
            if not os.path.exists(base_dir):
                os.makedirs(base_dir, exist_ok=True)
        
        file_path = os.path.join(base_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Ingest
        result = await knowledge_service.ingest_markdown_file(file_path, namespace)
        
        return {
            "status": "success", 
            "filename": file.filename, 
            "result": result,
            "path": os.relpath(file_path, os.getcwd())
        }
    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

class StrategyConfig(BaseModel):
    filename: Optional[str] = None # Optional now, used for context if single file click
    is_strategic_pivot: bool
    target_roles: List[str]
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
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings:
        settings = OrganizationSettings()
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
    result = await db.execute(select(OrganizationSettings).limit(1))
    settings = result.scalars().first()
    
    if not settings or not settings.selling_profile_json:
        return {"products": []}
        
    return json.loads(settings.selling_profile_json)

