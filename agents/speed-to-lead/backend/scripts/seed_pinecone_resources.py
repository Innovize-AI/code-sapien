"""
Embed resource metadata into Pinecone (resources namespace).

Reads from the DB resources table (populated by seed_supabase.py)
and upserts each resource's title+description into Pinecone.

Usage:
    poetry run python scripts/seed_pinecone_resources.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services import claude, pinecone_svc
from db.database import SessionLocal
from db.crud import list_resources


async def main() -> None:
    claude.init()
    pinecone_svc.init()

    async with SessionLocal() as db:
        rows = await list_resources(db)

    if not rows:
        print("No resources found in DB. Run seed_supabase.py first.")
        return

    resources = [
        {
            "id":            r.id,
            "title":         r.title,
            "description":   r.description or "",
            "resource_type": r.resource_type,
            "url":           r.url or "",
            "vertical":      r.vertical or "both",
        }
        for r in rows
    ]

    await pinecone_svc.upsert_resources(resources)

    for r in resources:
        print(f"  ✓ {r['id']} ({r['vertical']})")

    print(f"\nDone. {len(resources)} resources in Pinecone resources namespace.")


if __name__ == "__main__":
    asyncio.run(main())
