"""
Knowledge and resource management per firm.

Endpoints:
  POST   /firms/{firm_id}/knowledge/upload   — PDF → chunk → embed → Pinecone knowledge namespace
  GET    /firms/{firm_id}/resources          — list resources from DB
  POST   /firms/{firm_id}/resources          — add URL-based resource (YouTube link or external PDF)
  POST   /firms/{firm_id}/resources/upload   — upload PDF to Supabase Storage + save to DB + embed to Pinecone
  DELETE /firms/{firm_id}/resources/{res_id} — delete from DB + Pinecone
"""

import hashlib
import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from routes.guard import deny_agents
from services import pinecone_svc, supabase_svc

log = logging.getLogger(__name__)

router = APIRouter(prefix="/firms/{firm_id}", tags=["knowledge"], dependencies=[Depends(deny_agents)])

BUCKET = "resources"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resource_out(r) -> dict:
    return {
        "id":            r.id,
        "title":         r.title,
        "description":   r.description,
        "resource_type": r.resource_type,
        "url":           r.url,
        "firm_id":       str(r.firm_id) if r.firm_id else None,
        "updated_at":    r.updated_at.isoformat() if r.updated_at else None,
    }


def _chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + size]))
        i += size - overlap
    return chunks


async def _extract_pdf_text(data: bytes) -> str:
    import asyncio
    import fitz

    def _read():
        doc = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text().strip() for page in doc]
        doc.close()
        return "\n\n".join(p for p in pages if p)

    return await asyncio.to_thread(_read)


# ── Knowledge upload ──────────────────────────────────────────────────────────

@router.post("/knowledge/upload")
async def upload_knowledge(
    firm_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    db: AsyncSession = Depends(get_db),
):
    firm = await crud.get_firm(db, firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    data = await file.read()
    text = await _extract_pdf_text(data)
    if not text.strip():
        raise HTTPException(422, "Could not extract text from PDF — may be a scanned/image PDF")

    chunks = _chunk_text(text)
    docs = [
        {
            "id":       hashlib.md5(f"{firm_id}:{file.filename}:{i}".encode()).hexdigest(),
            "text":     chunk,
            "source":   file.filename,
            "doc_type": doc_type,
        }
        for i, chunk in enumerate(chunks)
    ]

    await pinecone_svc.upsert_knowledge(docs, firm_id=firm_id)
    log.info("Uploaded knowledge PDF firm=%s file=%s chunks=%d", firm_id, file.filename, len(docs))

    return {"ok": True, "filename": file.filename, "chunks": len(docs)}


# ── Resources ─────────────────────────────────────────────────────────────────

@router.get("/resources")
async def list_resources(firm_id: str, db: AsyncSession = Depends(get_db)):
    rows = await crud.list_resources(db, firm_id=firm_id)
    return [_resource_out(r) for r in rows]


@router.post("/resources")
async def add_resource(
    firm_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Add a URL-based resource (external PDF link or YouTube URL)."""
    firm = await crud.get_firm(db, firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")

    resource_id = body.get("id") or str(uuid.uuid4())[:8]
    row = {
        "id":            resource_id,
        "firm_id":       firm_id,
        "title":         body.get("title", ""),
        "description":   body.get("description", ""),
        "resource_type": body.get("resource_type", "pdf"),
        "url":           body.get("url", ""),
    }
    await crud.upsert_resource(db, row)

    # Embed into Pinecone resources namespace
    await pinecone_svc.upsert_resources([row], firm_id=firm_id)

    await pinecone_svc.load_resource_catalogue(db, firm_id=firm_id)
    return _resource_out(await crud.get_resource(db, resource_id))


@router.post("/resources/upload")
async def upload_resource(
    firm_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF to Supabase Storage, save metadata to DB, embed to Pinecone."""
    firm = await crud.get_firm(db, firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    data = await file.read()
    resource_id = str(uuid.uuid4())[:8]
    storage_path = f"{firm_id}/{resource_id}-{file.filename}"

    public_url = await supabase_svc.upload_file(BUCKET, storage_path, data, "application/pdf")

    row = {
        "id":            resource_id,
        "firm_id":       firm_id,
        "title":         title,
        "description":   description,
        "resource_type": "pdf",
        "url":           public_url,
    }
    await crud.upsert_resource(db, row)
    await pinecone_svc.upsert_resources([row], firm_id=firm_id)
    await pinecone_svc.load_resource_catalogue(db, firm_id=firm_id)

    log.info("Uploaded resource firm=%s file=%s url=%s", firm_id, file.filename, public_url)
    return _resource_out(await crud.get_resource(db, resource_id))


@router.delete("/resources/{resource_id}")
async def delete_resource(
    firm_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
):
    resource = await crud.get_resource(db, resource_id)
    if not resource or str(resource.firm_id) != firm_id:
        raise HTTPException(404, "Resource not found")

    await crud.delete_resource(db, resource_id)

    # Remove from Pinecone
    if pinecone_svc._index:
        import asyncio
        ns = pinecone_svc._ns(firm_id, "resources")
        await asyncio.to_thread(pinecone_svc._index.delete, ids=[resource_id], namespace=ns)

    await pinecone_svc.load_resource_catalogue(db, firm_id=firm_id)
    return {"ok": True}
