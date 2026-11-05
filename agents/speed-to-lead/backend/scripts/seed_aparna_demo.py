"""
Seed Aparna Constructions demo data into Pinecone for a specific firm.

Usage:
    poetry run python scripts/seed_aparna_demo.py --firm-id <uuid>

What this does:
  1. Chunks + embeds knowledge.txt  → {firm_id}-knowledge namespace
  2. Embeds portfolio.json          → {firm_id}-portfolio namespace
  3. Embeds resources.json          → {firm_id}-resources namespace
     (also upserts resource rows into the DB so they appear in the admin UI)

Run after creating the Aparna firm via the admin dashboard.
Get the firm UUID from the URL: /admin/firms/<uuid>
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services import claude, pinecone_svc
from db.database import SessionLocal
from db import crud

DOCS_DIR = os.path.join(os.path.dirname(__file__), "../../docs/aparna")

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50


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
    print(f"  Knowledge: {len(docs)} chunks → {firm_id}-knowledge")
    return len(docs)


async def seed_portfolio(firm_id: str) -> int:
    path = os.path.join(DOCS_DIR, "portfolio.json")
    with open(path, encoding="utf-8") as f:
        projects = json.load(f)

    await pinecone_svc.upsert_portfolio(projects, firm_id=firm_id)
    for p in projects:
        print(f"  Portfolio: {p['id']} — {p['title'][:60]}")
    return len(projects)


async def seed_resources(firm_id: str, db) -> int:
    from services import supabase_svc

    path = os.path.join(DOCS_DIR, "resources.json")
    with open(path, encoding="utf-8") as f:
        resources = json.load(f)

    seeded = []
    for r in resources:
        url = r.get("url")

        # URLs are already set (pre-uploaded to Supabase)

        row = {
            "id":            r["id"],
            "firm_id":       firm_id,
            "title":         r["title"],
            "description":   r["description"],
            "resource_type": r["resource_type"],
            "url":           url or "",
        }
        await crud.upsert_resource(db, row)
        seeded.append({**r, "url": url or ""})
        print(f"  Resource: {r['id']} ({r['resource_type']}) → DB")

    # Embed into Pinecone resources namespace
    await pinecone_svc.upsert_resources(seeded, firm_id=firm_id)
    print(f"  Resources: {len(seeded)} records → {firm_id}-resources")

    # Reload resource catalogue cache
    await pinecone_svc.load_resource_catalogue(db, firm_id=firm_id)
    return len(seeded)


async def main(firm_id: str) -> None:
    print(f"\nSeeding Aparna Constructions demo data for firm: {firm_id}\n")

    from services import supabase_svc
    claude.init()
    pinecone_svc.init()
    supabase_svc.init()

    async with SessionLocal() as db:
        firm = await crud.get_firm(db, firm_id)
        if not firm:
            print(f"ERROR: Firm {firm_id} not found in DB. Create it via the admin dashboard first.")
            sys.exit(1)

        print(f"Firm: {firm.name} (vertical={firm.vertical})\n")

        k = await seed_knowledge(firm_id)
        p = await seed_portfolio(firm_id)
        r = await seed_resources(firm_id, db)

    print(f"\nDone.")
    print(f"  Knowledge chunks : {k}")
    print(f"  Portfolio entries: {p}")
    print(f"  Resources        : {r}")
    print(f"\nNamespaces created:")
    print(f"  {firm_id}-knowledge")
    print(f"  {firm_id}-portfolio")
    print(f"  {firm_id}-resources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--firm-id", required=True, help="UUID of the Aparna firm from the DB")
    args = parser.parse_args()
    asyncio.run(main(args.firm_id))
