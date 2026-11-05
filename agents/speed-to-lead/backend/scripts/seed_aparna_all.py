"""
Full Aparna Constructions demo seed — one command does everything.

  poetry run python scripts/seed_aparna_all.py [--reset]

Steps:
  1. Create Aparna firm in DB (skips if already exists by name)
  2. Create Supabase Auth user aparna@speedtolead.ai
  3. Seed knowledge, portfolio, resources into Pinecone + DB

Credentials created:
  aparna@speedtolead.ai   SeedPass@123   counselor
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from services import claude, pinecone_svc, supabase_svc
from db.database import SessionLocal
from db import crud

DOCS_DIR = os.path.join(os.path.dirname(__file__), "../../docs/aparna")

CHUNK_SIZE    = 200
CHUNK_OVERLAP = 30

APARNA_FIRM = {
    "name":               "Aparna Constructions",
    "vertical":           "real_estate",
    "is_active":          True,
    "firm_display_name":  "Aparna Constructions",
    "visit_cta":          "free site visit (cab arranged)",
    "fallback_alert_email": "admin@innovizeai.com",
    # WA credentials left blank — fill in .env before going live
    "wa_phone_number_id": None,
    "meta_access_token":  None,
    "meta_app_secret":    None,
    "meta_webhook_verify_token": None,
}

APARNA_USER = {
    "email":    "aparna@speedtolead.ai",
    "password": "SeedPass@123",
}


# ── Supabase auth ─────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


def create_or_update_auth_user(email: str, password: str, firm_id: str) -> None:
    base = os.environ["SUPABASE_URL"]
    headers = _auth_headers()

    res = requests.get(
        f"{base}/auth/v1/admin/users",
        headers=headers,
        params={"filter": f"email.eq.{email}"},
    )
    existing = [u for u in res.json().get("users", []) if u.get("email") == email]

    metadata = {"name": "Aparna Counselor", "role": "counselor", "firm_id": firm_id}

    if existing:
        uid = existing[0]["id"]
        res = requests.put(
            f"{base}/auth/v1/admin/users/{uid}",
            headers=headers,
            json={"password": password, "user_metadata": metadata},
        )
        print(f"  Auth user updated : {email}")
    else:
        res = requests.post(
            f"{base}/auth/v1/admin/users",
            headers=headers,
            json={
                "email":         email,
                "password":      password,
                "email_confirm": True,
                "user_metadata": metadata,
            },
        )
        if res.ok:
            print(f"  Auth user created : {email}")
        else:
            print(f"  ERROR creating auth user: {res.text}")


# ── Pinecone seeding ──────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + CHUNK_SIZE]))
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def seed_knowledge(firm_id: str) -> int:
    path = os.path.join(DOCS_DIR, "knowledge.txt")
    with open(path, encoding="utf-8") as f:
        text = f.read()

    chunks = _chunk_text(text)
    docs = [
        {
            "id":       hashlib.md5(f"{firm_id}:knowledge:{i}".encode()).hexdigest(),
            "text":     chunk,
            "source":   "knowledge.txt",
            "doc_type": "knowledge",
        }
        for i, chunk in enumerate(chunks)
    ]

    await pinecone_svc.upsert_knowledge(docs, firm_id=firm_id)
    print(f"  Knowledge : {len(docs)} chunks → {firm_id}-knowledge")
    return len(docs)


async def seed_portfolio(firm_id: str) -> int:
    path = os.path.join(DOCS_DIR, "portfolio.json")
    with open(path, encoding="utf-8") as f:
        projects = json.load(f)

    await pinecone_svc.upsert_portfolio(projects, firm_id=firm_id)
    for p in projects:
        print(f"  Portfolio : {p['id']} — {p['title']}")
    return len(projects)


async def seed_resources(firm_id: str, db) -> int:
    path = os.path.join(DOCS_DIR, "resources.json")
    with open(path, encoding="utf-8") as f:
        resources = json.load(f)

    for r in resources:
        await crud.upsert_resource(db, {
            "id":            r["id"],
            "firm_id":       firm_id,
            "title":         r["title"],
            "description":   r["description"],
            "resource_type": r["resource_type"],
            "url":           r.get("url", ""),
        })
        print(f"  Resource  : {r['id']} ({r['resource_type']}) → DB")

    await pinecone_svc.upsert_resources(resources, firm_id=firm_id)
    await pinecone_svc.load_resource_catalogue(db, firm_id=firm_id)
    print(f"  Resources : {len(resources)} → {firm_id}-resources + catalogue cache")
    return len(resources)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(reset: bool) -> None:
    print("\nAparna Constructions — full demo seed\n")

    claude.init()
    pinecone_svc.init()
    supabase_svc.init()

    async with SessionLocal() as db:
        # 1. Firm
        firms = await crud.list_firms(db)
        existing_firm = next((f for f in firms if f.name == "Aparna Constructions"), None)

        if existing_firm and not reset:
            firm = existing_firm
            print(f"  Firm already exists: {firm.id}  (use --reset to recreate)")
        else:
            if existing_firm and reset:
                print(f"  Skipping firm delete (reset only re-seeds Pinecone + resources)")
                firm = existing_firm
            else:
                firm = await crud.create_firm(db, APARNA_FIRM)
                print(f"  Firm created : {firm.id}")

        firm_id = str(firm.id)
        print(f"  Firm ID: {firm_id}\n")

        # 2. Auth user
        create_or_update_auth_user(APARNA_USER["email"], APARNA_USER["password"], firm_id)
        print()

        # 3. Pinecone + DB resources
        k = await seed_knowledge(firm_id)
        p = await seed_portfolio(firm_id)
        r = await seed_resources(firm_id, db)

    print(f"""
Done.
  Knowledge chunks : {k}
  Portfolio entries: {p}
  Resources        : {r}

Login:
  URL      : http://localhost:3000
  Email    : {APARNA_USER["email"]}
  Password : {APARNA_USER["password"]}

Firm ID (for webhook / .env): {firm_id}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Re-seed even if firm already exists")
    args = parser.parse_args()
    asyncio.run(main(args.reset))
