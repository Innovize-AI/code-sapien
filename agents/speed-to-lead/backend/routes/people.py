"""
People and their WhatsApp numbers.

A person is a channel partner or an internal team member (a row in the brokers table). A firm
can register several WhatsApp numbers and attach each to one person. A person can have a
sign-in so they see, and chat on, only the conversations that arrive on their own numbers.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.database import get_db
from db.models import Broker
from routes.guard import deny_agents
from services import auth
from services import numbers as numbers_svc

router = APIRouter(tags=["people"], dependencies=[Depends(deny_agents)])


class NumberIn(BaseModel):
    firm_id: UUID
    label: str
    wa_phone_number_id: str
    display_phone: str | None = None
    person_id: UUID | None = None
    meta_access_token: str | None = None


class NumberPatch(BaseModel):
    label: str | None = None
    display_phone: str | None = None
    is_active: bool | None = None
    person_id: UUID | None = None
    detach: bool = False                 # set true to remove the person from the number


class LoginIn(BaseModel):
    email: str
    password: str


@router.get("/numbers")
async def list_numbers(firm_id: UUID, person_id: UUID | None = None,
                       db: AsyncSession = Depends(get_db)):
    return await numbers_svc.list_numbers(db, firm_id, person_id)


@router.post("/numbers")
async def register_number(body: NumberIn, db: AsyncSession = Depends(get_db)):
    if not await crud.get_firm(db, body.firm_id):
        raise HTTPException(404, "Firm not found")
    try:
        n = await numbers_svc.create_number(
            db, firm_id=body.firm_id, label=body.label, wa_phone_number_id=body.wa_phone_number_id,
            display_phone=body.display_phone, person_id=body.person_id,
            meta_access_token=body.meta_access_token)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    person = await db.get(Broker, n.person_id) if n.person_id else None
    return numbers_svc.public(n, person)


@router.patch("/numbers/{number_id}")
async def change_number(number_id: UUID, body: NumberPatch, db: AsyncSession = Depends(get_db)):
    try:
        n = await numbers_svc.update_number(
            db, number_id, label=body.label, display_phone=body.display_phone,
            is_active=body.is_active,
            person_id=None if body.detach else (body.person_id if body.person_id else ...))
    except LookupError:
        raise HTTPException(404, "Number not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    person = await db.get(Broker, n.person_id) if n.person_id else None
    return numbers_svc.public(n, person)


@router.post("/people/{person_id}/login")
async def create_person_login(person_id: UUID, body: LoginIn, db: AsyncSession = Depends(get_db)):
    """Create the sign-in for a person. They log in with this email and password and see only
    the conversations on their own numbers."""
    person = await db.get(Broker, person_id)
    if person is None:
        raise HTTPException(404, "Person not found")
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Enter a valid email address")
    try:
        await auth.create_login(
            email, body.password, role="agent", firm_id=str(person.firm_id),
            person_id=str(person.id), name=person.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    person.email = email
    await db.commit()
    return {"id": str(person.id), "email": email}
