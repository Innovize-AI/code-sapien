import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from db.models import RFQSubmission
from workflow.state import RFQState

logger = logging.getLogger(__name__)


def _state_to_data(state: RFQState, status: str) -> dict:
    return {
        "rfq_id": state["rfq_id"],
        "source": state.get("source"),
        "sender": state.get("sender"),
        "subject": state.get("subject"),
        "email_id": state.get("email_id"),
        "thread_id": state.get("thread_id"),
        "buyer_name": state.get("buyer_name"),
        "buyer_contact": state.get("buyer_contact"),
        "delivery_location": state.get("delivery_location"),
        "rfq_deadline": state.get("rfq_deadline"),
        "special_instructions": state.get("special_instructions"),
        "urgency": state.get("urgency"),
        "complexity": state.get("complexity"),
        "category": state.get("category"),
        "line_items": state.get("line_items"),
        "catalog_matches": state.get("catalog_matches"),
        "feasibility": state.get("feasibility"),
        "unfulfillable_items": state.get("unfulfillable_items"),
        "line_pricing": state.get("line_pricing"),
        "subtotal": state.get("subtotal"),
        "total": state.get("total"),
        "pricing_confidence": state.get("pricing_confidence"),
        "draft_quote": state.get("draft_quote"),
        "pdf_path": state.get("pdf_path"),
        "dispatched_at": state.get("dispatched_at"),
        "status": status,
        "review_notes": state.get("review_notes"),
        "error": state.get("error"),
        "document_type": state.get("document_type") or "RFQ",
        "rfq_type": state.get("rfq_type") or "product",
        "freight_origin": state.get("freight_origin"),
        "freight_destination": state.get("freight_destination"),
        "freight_cargo_desc": state.get("freight_cargo_desc"),
        "freight_weight_kg": state.get("freight_weight_kg"),
        "freight_volume_cbm": state.get("freight_volume_cbm"),
        "freight_truck_type": state.get("freight_truck_type"),
        "freight_distance_km": state.get("freight_distance_km"),
        "freight_quote_amount": state.get("freight_quote_amount"),
    }


async def save_rfq(db: AsyncSession, state: RFQState, status: str):
    try:
        existing = await db.execute(
            select(RFQSubmission).where(RFQSubmission.rfq_id == state["rfq_id"])
        )
        record = existing.scalars().first()
        data = _state_to_data(state, status)

        if record:
            await db.execute(
                update(RFQSubmission)
                .where(RFQSubmission.rfq_id == state["rfq_id"])
                .values(**{k: v for k, v in data.items() if k != "rfq_id"})
            )
        else:
            db.add(RFQSubmission(**data))

        await db.commit()
    except Exception as e:
        logger.error(f"DB save failed for RFQ {state['rfq_id']}: {e}")
        await db.rollback()


async def get_rfq(db: AsyncSession, rfq_id: str) -> RFQSubmission | None:
    result = await db.execute(
        select(RFQSubmission).where(RFQSubmission.rfq_id == rfq_id)
    )
    return result.scalars().first()


async def list_rfqs(
    db: AsyncSession,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[RFQSubmission], int]:
    query = select(RFQSubmission).order_by(RFQSubmission.created_at.desc())
    if status:
        query = query.where(RFQSubmission.status == status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    items = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    return list(items), total


async def get_stats(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(
            RFQSubmission.status,
            func.count().label("cnt"),
            func.coalesce(func.sum(RFQSubmission.total), 0).label("val"),
        ).group_by(RFQSubmission.status)
    )).all()

    stats = {
        "total": 0,
        "dispatched": 0,
        "pending_review": 0,
        "processing": 0,
        "failed": 0,
        "total_value": 0.0,
    }
    for row in rows:
        stats["total"] += row.cnt
        stats["total_value"] += float(row.val)
        key = row.status.replace("pending_review", "pending_review")
        if key in stats:
            stats[key] = row.cnt
    return stats
