import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import Response
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func

from workflow.state import RFQState
from workflow.graph import graph
from services.pdf_extractor import extract_text
from db.database import get_db
from db.models import RFQSubmission
from db.crud import save_rfq, get_rfq, list_rfqs, get_stats
from db.schemas import (
    RFQUploadResponse, RFQListResponse, RFQDetail, RFQListItem,
    StatsResponse, TextRFQRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("/tmp/rfq_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _blank_state(rfq_id: str, source: str, sender: str, raw_content: str,
                 subject: str | None = None, attachment_path: str | None = None,
                 attachment_url: str | None = None) -> RFQState:
    return RFQState(
        rfq_id=rfq_id,
        source=source,
        sender=sender,
        raw_content=raw_content,
        attachment_path=attachment_path,
        attachment_url=attachment_url,
        subject=subject,
        document_type=None,
        rfq_type=None,
        line_items=[],
        missing_fields=[],
        buyer_name=None,
        buyer_contact=None,
        delivery_location=None,
        rfq_deadline=None,
        urgency="standard",
        complexity="auto",
        category=None,
        catalog_matches=[],
        feasibility=[],
        unfulfillable_items=[],
        line_pricing=[],
        subtotal=0.0,
        total=0.0,
        pricing_confidence=0.0,
        freight_origin=None,
        freight_destination=None,
        freight_cargo_desc=None,
        freight_weight_kg=None,
        freight_volume_cbm=None,
        freight_truck_type=None,
        freight_distance_km=None,
        freight_quote_amount=None,
        draft_quote=None,
        pdf_path=None,
        status="processing",
        review_notes=None,
        error=None,
    )


# ---------------------------------------------------------------------------
# Submit via file upload
# ---------------------------------------------------------------------------

@router.post("/rfq/upload", response_model=RFQUploadResponse)
async def upload_rfq(
    file: UploadFile = File(...),
    sender: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    rfq_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{rfq_id}_{file.filename}"
    file_path.write_bytes(await file.read())

    try:
        raw_text = extract_text(str(file_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    initial_state = _blank_state(rfq_id, "upload", sender, raw_text,
                                  subject=file.filename, attachment_path=str(file_path))
    config = {"configurable": {"thread_id": rfq_id}}
    result = await graph.ainvoke(initial_state, config=config)

    await save_rfq(db, result, result["status"])

    return RFQUploadResponse(
        rfq_id=rfq_id,
        status=result["status"],
        total=result.get("total"),
        pricing_confidence=result.get("pricing_confidence"),
        line_items_count=len(result.get("line_items") or []),
        draft_quote=result.get("draft_quote"),
        review_notes=result.get("review_notes"),
        rfq_type=result.get("rfq_type"),
    )


# ---------------------------------------------------------------------------
# Submit via plain text (freight / quick paste)
# ---------------------------------------------------------------------------

@router.post("/rfq/text", response_model=RFQUploadResponse)
async def submit_text_rfq(
    body: TextRFQRequest,
    db: AsyncSession = Depends(get_db),
):
    rfq_id = str(uuid.uuid4())
    initial_state = _blank_state(rfq_id, "upload", body.sender, body.raw_text,
                                  subject=body.subject or "Text RFQ")
    config = {"configurable": {"thread_id": rfq_id}}
    result = await graph.ainvoke(initial_state, config=config)

    await save_rfq(db, result, result["status"])

    return RFQUploadResponse(
        rfq_id=rfq_id,
        status=result["status"],
        total=result.get("total"),
        pricing_confidence=result.get("pricing_confidence"),
        line_items_count=len(result.get("line_items") or []),
        draft_quote=result.get("draft_quote"),
        review_notes=result.get("review_notes"),
        rfq_type=result.get("rfq_type"),
    )


# ---------------------------------------------------------------------------
# List + stats
# ---------------------------------------------------------------------------

@router.get("/rfq/stats", response_model=StatsResponse)
async def rfq_stats(db: AsyncSession = Depends(get_db)):
    try:
        stats = await get_stats(db)
        return StatsResponse(**stats)
    except Exception as e:
        logger.warning(f"Stats query failed: {e}")
        return StatsResponse(total=0, dispatched=0, pending_review=0, processing=0, failed=0, total_value=0.0)


def _normalize_email_id(email_id: str | None) -> str | None:
    """Convert Gmail decimal message IDs to hex. Short all-digit strings are
    legacy IMAP sequence numbers that can't be resolved — return None for those."""
    if not email_id:
        return email_id
    if email_id.isdigit():
        # Gmail decimal IDs are 18-19 digits; IMAP seq numbers are short
        if len(email_id) >= 15:
            return hex(int(email_id))[2:]
        return None  # stale IMAP seq number — no recoverable hex ID
    return email_id


@router.get("/rfq", response_model=RFQListResponse)
async def list_rfq(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        items, total = await list_rfqs(db, status=status, page=page, limit=limit)
    except Exception as e:
        logger.warning(f"List RFQ failed: {e}")
        items, total = [], 0
    normalized = []
    for rec in items:
        item = RFQListItem.model_validate(rec)
        item.email_id = _normalize_email_id(item.email_id)
        normalized.append(item)
    return RFQListResponse(items=normalized, total=total, page=page, limit=limit)


# ---------------------------------------------------------------------------
# Detail / status / draft
# ---------------------------------------------------------------------------


@router.get("/rfq/{rfq_id}", response_model=RFQDetail)
async def get_rfq_detail(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    data = RFQDetail.model_validate(record)
    data.email_id = _normalize_email_id(data.email_id)
    return data


@router.get("/rfq/{rfq_id}/status")
async def get_status(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return {"rfq_id": rfq_id, "status": record.status}


@router.get("/rfq/{rfq_id}/draft")
async def get_draft(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return {"rfq_id": rfq_id, "draft_quote": record.draft_quote, "status": record.status, "total": record.total}


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------

@router.post("/rfq/{rfq_id}/approve")
async def approve_rfq(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if record.status not in ("pending_review", "failed"):
        raise HTTPException(status_code=400, detail=f"Cannot approve RFQ with status '{record.status}'")

    dispatched = False
    if record.draft_quote and record.sender:
        try:
            import os
            from services.email_service import send_quotation_email
            from services.pdf_service import generate_quote_pdf

            pdf_bytes = generate_quote_pdf(record)

            excel_bytes = None
            excel_filename = None
            if record.attachment_path and os.path.exists(record.attachment_path):
                suffix = record.attachment_path.rsplit(".", 1)[-1].lower() if "." in record.attachment_path else ""
                if suffix in ("xlsx", "xlsm", "xls", "csv"):
                    from services.excel_filler import fill_excel_template
                    excel_bytes = fill_excel_template(record.attachment_path, record.line_pricing or [])
                    # Remove the RFQ ID prefix from filename for the email attachment
                    base_name = os.path.basename(record.attachment_path)
                    clean_name = base_name.split("_", 1)[-1] if "_" in base_name else base_name
                    excel_filename = f"Quoted_{clean_name}"

            dispatched = send_quotation_email(
                to=record.sender,
                rfq_id=rfq_id,
                buyer_name=record.buyer_name or "Valued Customer",
                draft_quote=record.draft_quote,
                total=record.total or 0.0,
                pdf_bytes=pdf_bytes,
                excel_bytes=excel_bytes,
                excel_filename=excel_filename,
            )
        except Exception as e:
            logger.warning(f"Email dispatch failed for {rfq_id}: {e}", exc_info=True)

    await db.execute(
        update(RFQSubmission)
        .where(RFQSubmission.rfq_id == rfq_id)
        .values(status="dispatched", dispatched_at=func.now())
    )
    await db.commit()
    return {"rfq_id": rfq_id, "status": "dispatched", "email_sent": dispatched}


@router.post("/rfq/{rfq_id}/reject")
async def reject_rfq(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    await db.execute(
        update(RFQSubmission).where(RFQSubmission.rfq_id == rfq_id).values(status="rejected")
    )
    await db.commit()
    return {"rfq_id": rfq_id, "status": "rejected"}


# ---------------------------------------------------------------------------
# Agent trace
# ---------------------------------------------------------------------------

@router.get("/rfq/{rfq_id}/trace")
async def get_trace(rfq_id: str):
    from services.trace_store import get_trace as _get_trace
    return {"steps": _get_trace(rfq_id)}

# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

@router.get("/rfq/{rfq_id}/pdf")
async def download_pdf(rfq_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_rfq(db, rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    try:
        from services.pdf_service import generate_quote_pdf
        pdf_bytes = generate_quote_pdf(record)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    filename = f"quote-{rfq_id[:8].upper()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
