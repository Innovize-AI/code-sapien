"""
WhatsApp numbers registered for a firm, each optionally attached to one person.

A firm's own main number lives on firms.wa_phone_number_id. Extra numbers live in firm_numbers
and belong to a person (a channel partner or an internal team member). A conversation that
arrives on a person's number is owned by that person. Replies leave from the same number.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Broker, Firm, FirmNumber

log = logging.getLogger(__name__)


async def resolve(db: AsyncSession, wa_phone_number_id: str | None) -> tuple[Firm | None, FirmNumber | None]:
    """Find the firm, and the person's number when the message came in on one.
    Numbers registered under a person are checked first, then the firm's main number."""
    if not wa_phone_number_id:
        return None, None

    number = (await db.execute(
        select(FirmNumber).where(FirmNumber.wa_phone_number_id == wa_phone_number_id,
                                 FirmNumber.is_active.is_(True))
    )).scalar_one_or_none()
    if number is not None:
        firm = (await db.execute(
            select(Firm).where(Firm.id == number.firm_id, Firm.is_active.is_(True))
        )).scalar_one_or_none()
        return (firm, number) if firm else (None, None)

    firm = (await db.execute(
        select(Firm).where(Firm.wa_phone_number_id == wa_phone_number_id, Firm.is_active.is_(True))
    )).scalar_one_or_none()
    return firm, None


def credentials(firm: Firm, number: FirmNumber | None) -> tuple[str | None, str | None]:
    """(access_token, wa_phone_number_id) to send from. A number can carry its own token, otherwise
    it uses the firm's."""
    if number is None:
        return firm.meta_access_token, firm.wa_phone_number_id
    return (number.meta_access_token or firm.meta_access_token), number.wa_phone_number_id


async def number_for_lead(db: AsyncSession, number_id) -> FirmNumber | None:
    return await db.get(FirmNumber, number_id) if number_id else None


def public(n: FirmNumber, person: Broker | None = None) -> dict:
    """API shape. The access token is never returned, only whether one is set."""
    return {
        "id": str(n.id),
        "firm_id": str(n.firm_id),
        "person_id": str(n.person_id) if n.person_id else None,
        "person_name": person.name if person else None,
        "person_kind": person.kind if person else None,
        "label": n.label,
        "display_phone": n.display_phone,
        "wa_phone_number_id": n.wa_phone_number_id,
        "has_own_token": bool(n.meta_access_token),
        "is_active": bool(n.is_active),
        "created_at": n.created_at,
    }


async def list_numbers(db: AsyncSession, firm_id, person_id=None) -> list[dict]:
    q = select(FirmNumber).where(FirmNumber.firm_id == firm_id)
    if person_id:
        q = q.where(FirmNumber.person_id == person_id)
    rows = list((await db.execute(q.order_by(FirmNumber.created_at))).scalars())
    people = {p.id: p for p in (await db.execute(
        select(Broker).where(Broker.firm_id == firm_id))).scalars()}
    return [public(n, people.get(n.person_id)) for n in rows]


async def create_number(db: AsyncSession, *, firm_id, label: str, wa_phone_number_id: str,
                        display_phone: str | None = None, person_id=None,
                        meta_access_token: str | None = None) -> FirmNumber:
    wa_id = (wa_phone_number_id or "").strip()
    if not wa_id:
        raise ValueError("Enter the WhatsApp phone number ID from Meta")
    if not (label or "").strip():
        raise ValueError("Give the number a label")

    taken = (await db.execute(select(FirmNumber.id).where(FirmNumber.wa_phone_number_id == wa_id))).first()
    main = (await db.execute(select(Firm.id).where(Firm.wa_phone_number_id == wa_id))).first()
    if taken or main:
        raise ValueError("That WhatsApp number ID is already registered")

    if person_id:
        person = await db.get(Broker, person_id)
        if person is None or person.firm_id != firm_id:
            raise ValueError("That person does not belong to this firm")

    n = FirmNumber(firm_id=firm_id, person_id=person_id, label=label.strip(),
                   display_phone=(display_phone or "").strip() or None,
                   wa_phone_number_id=wa_id,
                   meta_access_token=(meta_access_token or "").strip() or None)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def update_number(db: AsyncSession, number_id: UUID, *, label: str | None = None,
                        person_id=..., is_active: bool | None = None,
                        display_phone: str | None = None) -> FirmNumber:
    n = await db.get(FirmNumber, number_id)
    if n is None:
        raise LookupError("Number not found")
    if label:
        n.label = label.strip()
    if display_phone is not None:
        n.display_phone = display_phone.strip() or None
    if is_active is not None:
        n.is_active = is_active
    if person_id is not ...:
        if person_id is not None:
            person = await db.get(Broker, person_id)
            if person is None or person.firm_id != n.firm_id:
                raise ValueError("That person does not belong to this firm")
        n.person_id = person_id
    await db.commit()
    await db.refresh(n)
    return n
