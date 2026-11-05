"""
Create sign-ins for Aparna Constructions: one counselor and two agents (a channel partner and an
internal team member). Safe to re-run: existing accounts are updated, not duplicated.

  counselor  aparna@speedtolead.ai           sees every Aparna conversation
  agent      aparna.partner@speedtolead.ai   a channel partner, sees only their own numbers
  agent      aparna.team@speedtolead.ai      a team member, sees only their own numbers

All passwords: SeedPass@123  (change them before sharing with anyone outside the team)

The two agents need a person record to be tied to, so this also adds two people to the Aparna firm
if they are not there yet. No WhatsApp numbers are registered here: add the real ones from
Partners and team, then the person's page, then Register a number.

    python scripts/seed_aparna_logins.py --dry-run     # show what would happen, change nothing
    python scripts/seed_aparna_logins.py               # do it
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import requests  # noqa: E402
from sqlalchemy import select  # noqa: E402

from db.database import SessionLocal, engine  # noqa: E402
from db.models import Broker, Firm  # noqa: E402
from services import broker_registry as reg  # noqa: E402

PASSWORD = "SeedPass@123"
FIRM_NAME = "Aparna Constructions"

# phone numbers here are placeholders for the two sample people, not real people
PEOPLE = [
    {"key": "partner", "kind": "partner", "name": "Aparna Partner", "company": "Sample Realty",
     "phone": "9000000101", "email": "aparna.partner@speedtolead.ai"},
    {"key": "team", "kind": "team", "name": "Aparna Sales Executive", "company": "Aparna sales team",
     "phone": "9000000102", "email": "aparna.team@speedtolead.ai"},
]
COUNSELOR_EMAIL = "aparna@speedtolead.ai"


def _headers():
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def upsert_user(email: str, metadata: dict, dry: bool) -> str:
    """Create the account, or update its password and metadata when it already exists."""
    if dry:
        return "would create or update"
    base = os.environ["SUPABASE_URL"].rstrip("/")
    found = requests.get(f"{base}/auth/v1/admin/users", headers=_headers(),
                         params={"filter": f"email.eq.{email}"}, timeout=20)
    existing = [u for u in found.json().get("users", []) if u.get("email") == email]
    if existing:
        r = requests.put(f"{base}/auth/v1/admin/users/{existing[0]['id']}", headers=_headers(),
                         json={"password": PASSWORD, "user_metadata": metadata}, timeout=20)
        return "updated" if r.ok else f"ERROR {r.text[:120]}"
    r = requests.post(f"{base}/auth/v1/admin/users", headers=_headers(),
                      json={"email": email, "password": PASSWORD, "email_confirm": True,
                            "user_metadata": metadata}, timeout=20)
    return "created" if r.ok else f"ERROR {r.text[:120]}"


async def main(dry: bool):
    async with SessionLocal() as db:
        firm = (await db.execute(select(Firm).where(Firm.name == FIRM_NAME))).scalar_one_or_none()
        if firm is None:
            sys.exit(f"Firm not found: {FIRM_NAME}")
        firm_id = str(firm.id)
        print(f"Firm: {firm.name} ({firm_id})\n")

        rows = []
        # counselor
        status = upsert_user(COUNSELOR_EMAIL, {"name": "Aparna Counselor", "role": "counselor",
                                               "firm_id": firm_id}, dry)
        rows.append((COUNSELOR_EMAIL, "counselor", "all Aparna conversations", status))

        # agents, each tied to a person in the firm
        for p in PEOPLE:
            person = (await db.execute(select(Broker).where(
                Broker.firm_id == firm.id, Broker.phone10 == reg.phone10(p["phone"])))).scalar_one_or_none()
            note = "existing person"
            if person is None:
                note = "new person"
                if not dry:
                    person = await reg.create_broker(db, firm.id, p["name"], p["phone"],
                                                     company=p["company"], kind=p["kind"])
            if person is not None and not dry:
                person.email = p["email"]
                await db.commit()
            person_id = str(person.id) if person is not None else "(created on a real run)"
            status = upsert_user(p["email"], {"name": p["name"], "role": "agent", "firm_id": firm_id,
                                              "person_id": person_id}, dry)
            rows.append((p["email"], "agent", f"{p['kind']}, {note}", status))

    await engine.dispose()
    print(f"{'Email':<34}{'Role':<11}{'Scope':<36}Result")
    for r in rows:
        print(f"{r[0]:<34}{r[1]:<11}{r[2]:<36}{r[3]}")
    print(f"\nPassword for all: {PASSWORD}")
    if dry:
        print("Dry run: nothing was created or changed.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.dry_run))
