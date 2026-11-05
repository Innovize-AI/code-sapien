"""
Broker registry: channel partner enrolment, timestamped client registration,
duplicate and conflict handling, coded-link attribution, and the numbers behind
the dashboard (source split, broker leaderboard).

Rules (see workspace/marketing/offers/.../speed-to-lead-broker-channel-pivot.md, section 2.1):
  * A broker's identity is their personal WhatsApp number, enrolled in advance by the developer.
  * A registration is a ledger entry. It never makes the agent message the client.
  * First valid registration for a client and project wins. A competing attempt is stored as
    a duplicate and sent to a human. Nothing is auto-resolved.
  * A buyer who taps a broker's coded link and sends the first message is attributed
    automatically, with the buyer's own first-contact time as the timestamp.

The text helpers at the top are pure functions so they can be tested without a database.
"""

from __future__ import annotations

import logging
import re
import secrets
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Broker, ConversationLog, Lead, LeadRegistration, Project, Visit,
)

log = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_VALIDITY_DAYS = 60
_REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ══ Pure helpers ═════════════════════════════════════════════════════════════

def phone10(raw: str | None) -> str | None:
    """Last 10 digits of an Indian mobile number, or None if there are fewer than 10."""
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else None


def mask_phone(p10: str | None) -> str:
    return f"{p10[:2]}XXXXXX{p10[-2:]}" if p10 and len(p10) == 10 else (p10 or "")


_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")
_CMD_RE = re.compile(r"^\s*(?:reg(?:ister)?|new)\b[\s:,-]*", re.IGNORECASE)
_STATUS_RE = re.compile(r"^\s*status\b[\s:,-]*(REG-[A-Z0-9]{4,10})", re.IGNORECASE)
_CODE_RE = re.compile(r"^\s*#?(BRK-?[A-Z0-9]{3,8})\b[\s:,-]*", re.IGNORECASE)


@dataclass
class ParsedRegistration:
    name: str | None
    client_phone10: str
    project_hint: str | None


def looks_like_registration(text: str | None) -> bool:
    return bool(text and _CMD_RE.match(text) and _PHONE_RE.search(text))


def parse_registration(text: str | None) -> ParsedRegistration | None:
    """'REG Ravi Kumar 98765 43210 Skyline' -> name, phone10, project hint. Needs a mobile number."""
    if not text:
        return None
    m = _PHONE_RE.search(text)
    if not m:
        return None
    p10 = re.sub(r"\D", "", m.group(1))
    before = _CMD_RE.sub("", text[: m.start()], count=1)
    after = text[m.end():]
    name = re.sub(r"\s+", " ", re.sub(r"[,:;|\-]+", " ", before)).strip() or None
    hint = re.sub(r"\s+", " ", re.sub(r"^[\s,:;|\-]+", "", after)).strip() or None
    return ParsedRegistration(name=name, client_phone10=p10, project_hint=hint)


def parse_status_query(text: str | None) -> str | None:
    m = _STATUS_RE.match(text or "")
    return m.group(1).upper() if m else None


def extract_broker_code(text: str | None) -> tuple[str | None, str]:
    """'BRK-RAV7 floor plan please' -> ('BRK-RAV7', 'floor plan please')."""
    if not text:
        return None, text or ""
    m = _CODE_RE.match(text)
    if not m:
        return None, text
    raw = m.group(1).upper()
    code = raw if raw.startswith("BRK-") else "BRK-" + raw[3:]
    return code, text[m.end():].strip()


def new_reference() -> str:
    return "REG-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))


def make_broker_code(name: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", name).upper()[:3].ljust(3, "X")
    return f"BRK-{letters}{secrets.randbelow(10)}"


def fmt_ist(dt: datetime | None) -> str:
    if dt is None:
        return "unknown time"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    d = dt.astimezone(IST)
    hour = d.strftime("%I").lstrip("0") or "12"
    return f"{d.day:02d} {d.strftime('%b %Y')}, {hour}:{d.strftime('%M %p')} IST"


@dataclass
class RegView:
    """The few fields the decision needs, so it can be tested without ORM objects."""
    id: object
    broker_id: object
    registered_at: datetime
    valid_until: datetime | None
    status: str


@dataclass
class Decision:
    kind: str                       # new | already_mine | conflict_broker | conflict_lead
    first: RegView | None = None
    existing_lead_at: datetime | None = None


def is_active(reg: RegView, now: datetime) -> bool:
    return reg.status == "registered" and (reg.valid_until is None or reg.valid_until > now)


def decide(broker_id, active_regs: list[RegView], existing_lead_at: datetime | None,
           now: datetime) -> Decision:
    """First valid registration wins. Order matters: broker registrations are checked
    before the developer's own lead, because a prior broker registration is the older claim."""
    live = sorted((r for r in active_regs if is_active(r, now)), key=lambda r: r.registered_at)
    for r in live:
        if r.broker_id == broker_id:
            return Decision("already_mine", first=r)
    if live:
        return Decision("conflict_broker", first=live[0])
    if existing_lead_at is not None:
        return Decision("conflict_lead", existing_lead_at=existing_lead_at)
    return Decision("new")


# ── Message text (no em-dashes, no exclamation marks) ────────────────────────

HELP_TEXT = (
    "To register a client, send:\n"
    "REG client name, mobile number, project\n"
    "Example: REG Ravi Kumar 9876543210 Skyline Heights\n"
    "To check a registration, send: STATUS REG-XXXXXX"
)


def receipt_text(reg: LeadRegistration, project: Project | None, firm_name: str) -> str:
    return (
        f"Registered with {firm_name}.\n"
        f"Reference: {reg.reference_id}\n"
        f"Client: {reg.client_name or 'Name not given'} ({mask_phone(reg.client_phone10)})\n"
        f"Project: {project.name if project else 'Not specified'}\n"
        f"Registered: {fmt_ist(reg.registered_at)}\n"
        f"Valid until: {fmt_ist(reg.valid_until)}\n"
        "This is your proof of registration. The sales team confirms next steps with you."
    )


def already_mine_text(reg: LeadRegistration, project: Project | None) -> str:
    return (
        f"You already registered this client{' for ' + project.name if project else ''}.\n"
        f"Reference: {reg.reference_id}\n"
        f"Registered: {fmt_ist(reg.registered_at)}\n"
        f"Valid until: {fmt_ist(reg.valid_until)}"
    )


def conflict_broker_text(attempt: LeadRegistration, first: LeadRegistration,
                         project: Project | None) -> str:
    return (
        f"This client is already registered{' for ' + project.name if project else ''} "
        f"since {fmt_ist(first.registered_at)}.\n"
        f"Your attempt is recorded as {attempt.reference_id} at {fmt_ist(attempt.registered_at)}.\n"
        "The sales head reviews every conflict and will contact you."
    )


def conflict_lead_text(attempt: LeadRegistration, lead_at: datetime,
                       project: Project | None) -> str:
    return (
        f"This client is already in the developer's system since {fmt_ist(lead_at)}"
        f"{' for ' + project.name if project else ''}.\n"
        f"Your attempt is recorded as {attempt.reference_id} at {fmt_ist(attempt.registered_at)}.\n"
        "The sales head reviews every conflict and will contact you."
    )


def rejected_text(firm_name: str) -> str:
    return (
        f"This number is not enrolled as a channel partner with {firm_name}. "
        "Ask the sales team to add you, then send the registration again."
    )


# ══ Database operations ══════════════════════════════════════════════════════

def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BrokerReply:
    text: str
    kind: str                       # registered | already_mine | conflict | rejected | help | status | ask_project | suspended
    registration_id: str | None = None
    reference_id: str | None = None
    conflict: bool = False


@dataclass
class Outcome:
    kind: str                       # new | already_mine | conflict_broker | conflict_lead
    registration: LeadRegistration
    first: LeadRegistration | None = None
    existing_lead_at: datetime | None = None
    project: Project | None = None


async def get_broker_by_phone(db: AsyncSession, firm_id, phone: str | None) -> Broker | None:
    p10 = phone10(phone)
    if not p10:
        return None
    r = await db.execute(select(Broker).where(Broker.firm_id == firm_id, Broker.phone10 == p10))
    return r.scalar_one_or_none()


async def get_broker_by_code(db: AsyncSession, firm_id, code: str) -> Broker | None:
    r = await db.execute(select(Broker).where(Broker.firm_id == firm_id, Broker.code == code))
    return r.scalar_one_or_none()


async def list_projects(db: AsyncSession, firm_id, active_only: bool = True) -> list[Project]:
    q = select(Project).where(Project.firm_id == firm_id)
    if active_only:
        q = q.where(Project.is_active.is_(True))
    r = await db.execute(q.order_by(Project.created_at))
    return list(r.scalars())


async def resolve_project(db: AsyncSession, firm_id, hint: str | None
                          ) -> tuple[Project | None, list[Project]]:
    """Returns (project, candidates). project is None when the hint is missing or ambiguous."""
    projects = await list_projects(db, firm_id)
    if not projects:
        return None, []
    if hint:
        h = hint.lower()
        hits = [p for p in projects if h in p.name.lower() or p.name.lower() in h]
        if len(hits) == 1:
            return hits[0], projects
        words = [w for w in re.split(r"\W+", h) if len(w) > 2]
        hits = [p for p in projects if any(w in p.name.lower() for w in words)]
        if len(hits) == 1:
            return hits[0], projects
        return None, projects
    if len(projects) == 1:
        return projects[0], projects
    return None, projects


async def create_broker(db: AsyncSession, firm_id, name: str, phone: str,
                        company: str | None = None, rera_agent_no: str | None = None,
                        kind: str = "partner") -> Broker:
    p10 = phone10(phone)
    if not p10:
        raise ValueError("Enter a 10 digit mobile number")
    existing = await get_broker_by_phone(db, firm_id, p10)
    if existing:
        raise ValueError("A broker with this number is already enrolled")
    for _ in range(12):
        code = make_broker_code(name)
        if not await get_broker_by_code(db, firm_id, code):
            break
    else:
        raise ValueError("Could not generate a unique broker code")
    if kind not in ("partner", "team"):
        raise ValueError("kind must be partner or team")
    broker = Broker(firm_id=firm_id, name=name.strip(), company=company, phone=phone.strip(),
                    phone10=p10, rera_agent_no=rera_agent_no, code=code, kind=kind)
    db.add(broker)
    await db.commit()
    await db.refresh(broker)
    return broker


async def _regs_for_client(db: AsyncSession, firm_id, p10: str, project_id) -> list[LeadRegistration]:
    q = select(LeadRegistration).where(
        LeadRegistration.firm_id == firm_id,
        LeadRegistration.client_phone10 == p10,
        LeadRegistration.status == "registered",
    )
    q = q.where(LeadRegistration.project_id == project_id) if project_id else q.where(
        LeadRegistration.project_id.is_(None))
    r = await db.execute(q)
    return list(r.scalars())


async def _existing_direct_lead_at(db: AsyncSession, firm_id, p10: str) -> datetime | None:
    r = await db.execute(
        select(func.min(Lead.created_at)).where(
            Lead.firm_id == firm_id,
            func.right(Lead.phone, 10) == p10,
            Lead.broker_id.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def register_client(
    db: AsyncSession, *, firm, broker: Broker, client_phone10: str, client_name: str | None,
    project: Project | None, method: str = "broker_whatsapp", wamid: str | None = None,
    submitted_by: str | None = None, lead_id=None, registered_at: datetime | None = None,
    existing_lead_at: datetime | None = None, check_existing_lead: bool = True,
) -> Outcome:
    now = registered_at or _now()
    project_id = project.id if project else None
    regs = await _regs_for_client(db, firm.id, client_phone10, project_id)
    views = [RegView(r.id, r.broker_id, r.registered_at, r.valid_until, r.status) for r in regs]

    lead_at = existing_lead_at
    if lead_at is None and check_existing_lead:
        lead_at = await _existing_direct_lead_at(db, firm.id, client_phone10)
    decision = decide(broker.id, views, lead_at, now)

    if decision.kind == "already_mine":
        mine = next(r for r in regs if r.id == decision.first.id)
        return Outcome("already_mine", mine, project=project)

    validity = (project.validity_days if project and project.validity_days else DEFAULT_VALIDITY_DAYS)
    reg = LeadRegistration(
        firm_id=firm.id, project_id=project_id, broker_id=broker.id, lead_id=lead_id,
        reference_id=new_reference(), client_name=client_name, client_phone10=client_phone10,
        method=method, submitted_by_phone=submitted_by, source_wamid=wamid,
        registered_at=now, valid_until=now + timedelta(days=validity),
    )
    first = None
    if decision.kind == "conflict_broker":
        first = next(r for r in regs if r.id == decision.first.id)
        reg.status = "duplicate"
        reg.conflict_with = first.id
        reg.conflict_kind = "broker_vs_broker"
        reg.conflict_state = "open"
    elif decision.kind == "conflict_lead":
        reg.status = "duplicate"
        reg.conflict_kind = "broker_vs_existing_lead"
        reg.conflict_state = "open"
    else:
        reg.status = "registered"

    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return Outcome(decision.kind, reg, first=first, existing_lead_at=decision.existing_lead_at,
                   project=project)


async def _wamid_seen(db: AsyncSession, wamid: str | None) -> LeadRegistration | None:
    if not wamid:
        return None
    r = await db.execute(select(LeadRegistration).where(LeadRegistration.source_wamid == wamid))
    return r.scalars().first()


async def handle_broker_message(db: AsyncSession, firm, from_phone: str, text: str | None,
                                wamid: str | None = None) -> BrokerReply | None:
    """Returns a reply when the message belongs to the broker channel, or None when the sender
    is an ordinary buyer and the normal lead pipeline should run."""
    text = (text or "").strip()
    broker = await get_broker_by_phone(db, firm.id, from_phone)
    firm_name = getattr(firm, "firm_display_name", None) or firm.name

    if broker is None:
        if looks_like_registration(text):
            p = parse_registration(text)
            seen = await _wamid_seen(db, wamid)
            if not seen:
                reg = LeadRegistration(
                    firm_id=firm.id, reference_id=new_reference(), client_name=p.name,
                    client_phone10=p.client_phone10, method="broker_whatsapp", status="rejected",
                    submitted_by_phone=from_phone, source_wamid=wamid,
                )
                db.add(reg)
                await db.commit()
                log.warning("Registration from unenrolled number %s for firm=%s", from_phone, firm.id)
            return BrokerReply(rejected_text(firm_name), "rejected")
        return None

    if broker.status != "active":
        return BrokerReply("Your partner access is paused. Please contact the sales team.", "suspended")

    ref = parse_status_query(text)
    if ref:
        r = await db.execute(select(LeadRegistration).where(
            LeadRegistration.reference_id == ref, LeadRegistration.broker_id == broker.id))
        reg = r.scalar_one_or_none()
        if not reg:
            return BrokerReply(f"No registration {ref} found for your number.", "status")
        return BrokerReply(
            f"{reg.reference_id}: {reg.status}. Registered {fmt_ist(reg.registered_at)}. "
            f"Valid until {fmt_ist(reg.valid_until)}.", "status", str(reg.id), reg.reference_id)

    parsed = parse_registration(text)
    if not parsed:
        return BrokerReply(HELP_TEXT, "help")

    seen = await _wamid_seen(db, wamid)
    if seen:  # Meta retry: answer again without creating a second record
        proj = await db.get(Project, seen.project_id) if seen.project_id else None
        return BrokerReply(receipt_text(seen, proj, firm_name), "registered", str(seen.id),
                           seen.reference_id)

    project, candidates = await resolve_project(db, firm.id, parsed.project_hint)
    if project is None and len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        return BrokerReply(f"Which project? Send the registration again with the project name. "
                           f"Active projects: {names}.", "ask_project")

    out = await register_client(
        db, firm=firm, broker=broker, client_phone10=parsed.client_phone10,
        client_name=parsed.name, project=project, wamid=wamid, submitted_by=from_phone)
    reg = out.registration
    if out.kind == "already_mine":
        return BrokerReply(already_mine_text(reg, project), "already_mine", str(reg.id),
                           reg.reference_id)
    if out.kind == "conflict_broker":
        return BrokerReply(conflict_broker_text(reg, out.first, project), "conflict", str(reg.id),
                           reg.reference_id, conflict=True)
    if out.kind == "conflict_lead":
        return BrokerReply(conflict_lead_text(reg, out.existing_lead_at, project), "conflict",
                           str(reg.id), reg.reference_id, conflict=True)
    return BrokerReply(receipt_text(reg, project, firm_name), "registered", str(reg.id),
                       reg.reference_id)


@dataclass
class CodedLinkResult:
    clean_text: str
    broker: Broker | None = None
    outcome: Outcome | None = None
    notify_text: str | None = None


async def attribute_coded_link(db: AsyncSession, firm, lead: Lead, text: str | None,
                               first_turn: bool, wamid: str | None = None) -> CodedLinkResult:
    """If the buyer's message starts with a broker code, attribute the lead to that broker."""
    code, remainder = extract_broker_code(text)
    if not code:
        return CodedLinkResult(text or "")
    broker = await get_broker_by_code(db, firm.id, code)
    if broker is None or broker.status != "active":
        return CodedLinkResult(remainder or (text or ""))

    if lead.broker_id is not None:  # first attribution stands
        return CodedLinkResult(remainder)

    project, _ = await resolve_project(db, firm.id, remainder or None)
    if project is None:
        projects = await list_projects(db, firm.id)
        project = projects[0] if len(projects) == 1 else None

    out = await register_client(
        db, firm=firm, broker=broker, client_phone10=phone10(lead.phone) or lead.phone[-10:],
        client_name=lead.wa_name, project=project, method="coded_link", wamid=wamid,
        lead_id=lead.id, registered_at=_now(),
        existing_lead_at=None if first_turn else lead.created_at,
        check_existing_lead=False,
    )
    firm_name = getattr(firm, "firm_display_name", None) or firm.name
    if out.kind == "new":
        await db.execute(update(Lead).where(Lead.id == lead.id).values(
            broker_id=broker.id, project_id=project.id if project else None, source="broker"))
        await db.commit()
        notify = (f"Your client {lead.wa_name or mask_phone(phone10(lead.phone))} opened your link"
                  f"{' for ' + project.name if project else ''} and is registered with {firm_name}.\n"
                  f"Reference: {out.registration.reference_id}\n"
                  f"Registered: {fmt_ist(out.registration.registered_at)}")
    elif out.kind == "already_mine":
        await db.execute(update(Lead).where(Lead.id == lead.id).values(
            broker_id=broker.id, project_id=project.id if project else None, source="broker"))
        await db.commit()
        notify = None
    else:
        notify = (f"A client opened your link but is already on record. Your attempt is "
                  f"{out.registration.reference_id}. The sales head reviews every conflict.")
    return CodedLinkResult(remainder, broker, out, notify)


# ── Conflict resolution (human only) ─────────────────────────────────────────

async def resolve_conflict(db: AsyncSession, registration_id, action: str, note: str | None,
                           by: str | None) -> LeadRegistration:
    """keep_first: the earlier claim stands. award_new: the contested attempt wins."""
    reg = await db.get(LeadRegistration, registration_id)
    if reg is None or reg.status != "duplicate":
        raise ValueError("Only an open duplicate can be resolved")
    if action not in ("keep_first", "award_new"):
        raise ValueError("action must be keep_first or award_new")
    now = _now()
    if action == "award_new":
        if reg.conflict_with:
            first = await db.get(LeadRegistration, reg.conflict_with)
            if first:
                first.status = "superseded"
        reg.status = "registered"
        if reg.lead_id and reg.broker_id:
            await db.execute(update(Lead).where(Lead.id == reg.lead_id).values(
                broker_id=reg.broker_id, project_id=reg.project_id, source="broker"))
    reg.conflict_state = "resolved"
    reg.resolution_note = (note or "").strip() or ("Earlier claim kept" if action == "keep_first"
                                                   else "Contested claim awarded")
    reg.resolved_by = by
    reg.resolved_at = now
    await db.commit()
    await db.refresh(reg)
    return reg


# ══ Read models for the dashboard ════════════════════════════════════════════

def _reg_dict(reg: LeadRegistration, broker: Broker | None, project: Project | None,
              first: LeadRegistration | None, first_broker: Broker | None) -> dict:
    return {
        "id": str(reg.id),
        "reference_id": reg.reference_id,
        "client_name": reg.client_name,
        "client_phone": mask_phone(reg.client_phone10),
        "client_phone_full": reg.client_phone10,
        "method": reg.method,
        "status": reg.status,
        "registered_at": reg.registered_at,
        "valid_until": reg.valid_until,
        "broker_id": str(reg.broker_id) if reg.broker_id else None,
        "broker_name": broker.name if broker else None,
        "broker_company": broker.company if broker else None,
        "submitted_by_phone": reg.submitted_by_phone,
        "project_id": str(reg.project_id) if reg.project_id else None,
        "project_name": project.name if project else None,
        "conflict_kind": reg.conflict_kind,
        "conflict_state": reg.conflict_state,
        "resolution_note": reg.resolution_note,
        "resolved_by": reg.resolved_by,
        "resolved_at": reg.resolved_at,
        "first": ({
            "reference_id": first.reference_id,
            "registered_at": first.registered_at,
            "broker_name": first_broker.name if first_broker else None,
        } if first else None),
    }


async def list_registrations(db: AsyncSession, firm_id, status: str | None = None,
                             broker_id=None, project_id=None, conflicts_only: bool = False,
                             limit: int = 200) -> list[dict]:
    q = select(LeadRegistration).where(LeadRegistration.firm_id == firm_id)
    if status:
        q = q.where(LeadRegistration.status == status)
    if broker_id:
        q = q.where(LeadRegistration.broker_id == broker_id)
    if project_id:
        q = q.where(LeadRegistration.project_id == project_id)
    if conflicts_only:
        q = q.where(LeadRegistration.conflict_state.isnot(None))
    regs = list((await db.execute(
        q.order_by(LeadRegistration.registered_at.desc()).limit(limit))).scalars())

    brokers = {b.id: b for b in (await db.execute(
        select(Broker).where(Broker.firm_id == firm_id))).scalars()}
    projects = {p.id: p for p in (await db.execute(
        select(Project).where(Project.firm_id == firm_id))).scalars()}
    by_id = {r.id: r for r in regs}
    missing = [r.conflict_with for r in regs if r.conflict_with and r.conflict_with not in by_id]
    if missing:
        for r in (await db.execute(select(LeadRegistration).where(
                LeadRegistration.id.in_(missing)))).scalars():
            by_id[r.id] = r
    out = []
    for r in regs:
        first = by_id.get(r.conflict_with) if r.conflict_with else None
        d = _reg_dict(r, brokers.get(r.broker_id), projects.get(r.project_id), first,
                      brokers.get(first.broker_id) if first else None)
        d["existing_lead_at"] = None
        if r.conflict_kind == "broker_vs_existing_lead":
            d["existing_lead_at"] = await _existing_direct_lead_at(db, firm_id, r.client_phone10)
        out.append(d)
    return out


async def leaderboard(db: AsyncSession, firm_id, days: int = 90) -> list[dict]:
    since = _now() - timedelta(days=days)
    brokers = list((await db.execute(
        select(Broker).where(Broker.firm_id == firm_id).order_by(Broker.created_at))).scalars())
    regs = list((await db.execute(select(LeadRegistration).where(
        LeadRegistration.firm_id == firm_id, LeadRegistration.registered_at >= since))).scalars())
    leads = list((await db.execute(select(Lead.id, Lead.broker_id).where(
        Lead.firm_id == firm_id, Lead.broker_id.isnot(None)))).all())
    visits = list((await db.execute(
        select(Visit.lead_id).where(Visit.firm_id == firm_id))).scalars())
    visit_leads = set(visits)

    rows = []
    for b in brokers:
        mine = [r for r in regs if r.broker_id == b.id]
        b_leads = [l.id for l in leads if l.broker_id == b.id]
        rows.append({
            "id": str(b.id), "name": b.name, "company": b.company, "phone": b.phone,
            "rera_agent_no": b.rera_agent_no, "code": b.code, "status": b.status,
            "kind": b.kind or "partner", "email": b.email,
            "registered": sum(1 for r in mine if r.status == "registered"),
            "conflicts": sum(1 for r in mine if r.status == "duplicate"),
            "superseded": sum(1 for r in mine if r.status == "superseded"),
            "leads": len(b_leads),
            "visits": sum(1 for lid in b_leads if lid in visit_leads),
            "last_registration_at": max((r.registered_at for r in mine), default=None),
            "created_at": b.created_at,
        })
    rows.sort(key=lambda x: (x["visits"], x["registered"], x["leads"]), reverse=True)
    return rows


def classify_source(broker_id, ctwa_source_id) -> str:
    if broker_id:
        return "broker"
    if ctwa_source_id:
        return "ad"
    return "organic"


async def source_split(db: AsyncSession, firm_id, days: int = 30) -> dict:
    since = _now() - timedelta(days=days)
    leads = list((await db.execute(select(
        Lead.id, Lead.broker_id, Lead.ctwa_source_id, Lead.created_at).where(
        Lead.firm_id == firm_id, Lead.created_at >= since))).all())
    ids = [l.id for l in leads]
    visit_leads = set()
    first_in: dict = {}
    first_out: dict = {}
    if ids:
        visit_leads = set((await db.execute(
            select(Visit.lead_id).where(Visit.lead_id.in_(ids)))).scalars())
        rows = (await db.execute(
            select(ConversationLog.lead_id, ConversationLog.direction,
                   func.min(ConversationLog.created_at)).where(
                ConversationLog.lead_id.in_(ids)).group_by(
                ConversationLog.lead_id, ConversationLog.direction))).all()
        for lead_id, direction, ts in rows:
            (first_in if direction == "inbound" else first_out)[lead_id] = ts

    buckets = {k: {"source": k, "leads": 0, "visits": 0, "_lat": []} for k in ("ad", "broker", "organic")}
    for l in leads:
        b = buckets[classify_source(l.broker_id, l.ctwa_source_id)]
        b["leads"] += 1
        if l.id in visit_leads:
            b["visits"] += 1
        if l.id in first_in and l.id in first_out and first_out[l.id] >= first_in[l.id]:
            b["_lat"].append((first_out[l.id] - first_in[l.id]).total_seconds())
    out = []
    for b in buckets.values():
        lat = b.pop("_lat")
        b["median_first_reply_seconds"] = round(statistics.median(lat), 1) if lat else None
        b["visit_rate"] = round(b["visits"] / b["leads"], 3) if b["leads"] else None
        out.append(b)

    open_conflicts = (await db.execute(select(func.count()).select_from(LeadRegistration).where(
        LeadRegistration.firm_id == firm_id, LeadRegistration.conflict_state == "open"))).scalar_one()
    return {"days": days, "sources": out, "open_conflicts": open_conflicts}


async def project_facts_text(db: AsyncSession, firm_id, project_id) -> str | None:
    """Plain-text facts about the buyer's project, for the system prompt.
    Uses the lead's project, or the firm's only active project."""
    if not firm_id:
        return None
    project = None
    if project_id:
        try:
            project = await db.get(Project, project_id)
        except Exception:
            project = None
    if project is None:
        projects = await list_projects(db, firm_id)
        project = projects[0] if len(projects) == 1 else None
    if project is None:
        return None
    lines = [f"Project: {project.name}"]
    if project.location:
        lines.append(f"Location: {project.location}")
    if project.rera_number:
        lines.append(f"RERA number: {project.rera_number}")
    if project.possession_date:
        lines.append(f"Possession: {project.possession_date.strftime('%B %Y')}")
    if project.starting_price:
        lines.append(f"Price: {project.starting_price}")
    if project.payment_plan:
        lines.append(f"Payment plan: {project.payment_plan}")
    if project.bank_tieups:
        lines.append(f"Home loan partners: {project.bank_tieups}")
    return "\n".join(lines)
