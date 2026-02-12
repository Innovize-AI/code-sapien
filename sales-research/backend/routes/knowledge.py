from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import os
from services.knowledge_service import KnowledgeService

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
async def get_namespaces():
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
async def list_knowledge_files():
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
async def ingest_file(request: IngestRequest):
    """
    Ingests a specific file into a namespace.
    """
    try:
        if request.file_path:
            # Ensure path is absolute or relative to project root
            full_path = request.file_path
            if not os.path.isabs(full_path):
                full_path = os.path.join(os.getcwd(), full_path)
            
            num_chunks = knowledge_service.ingest_markdown_file(
                full_path, 
                request.namespace, 
                request.metadata
            )
            return {"status": "success", "chunks": num_chunks}
        else:
            raise HTTPException(status_code=400, detail="Only file_path ingestion is currently supported.")
    except Exception as e:
        print(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-defaults")
async def sync_defaults(background_tasks: BackgroundTasks):
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
    
    def process_sync():
        for filename in files:
            path = os.path.join(base_dir, filename)
            # Route to namespaces based on filename
            namespace = "playbooks"
            if "case-study" in filename.lower():
                namespace = "case-studies"
            elif "one-pager" in filename.lower() or "offerings" in filename.lower():
                namespace = "solutions"
            
            try:
                knowledge_service.ingest_markdown_file(path, namespace)
            except Exception as e:
                print(f"Failed to ingest {filename}: {e}")

    background_tasks.add_task(process_sync)
    return {"status": "sync_started", "files_queued": len(files)}
