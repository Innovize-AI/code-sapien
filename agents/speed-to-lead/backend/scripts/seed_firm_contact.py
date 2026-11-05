"""
Add contact_phone / contact_email columns to firms and seed Aparna's values.

Usage:
    poetry run python scripts/seed_firm_contact.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from sqlalchemy import update, text
from db.database import SessionLocal
from db.models import Firm
from db.config import SCHEMA

FIRM_CONTACTS: dict[str, dict] = {
    "Aparna Constructions": {
        "contact_phone": "7095333335",
        "contact_email": "sales@aparnaconstructions.com",
    },
}


async def main() -> None:
    async with SessionLocal() as db:
        # Add columns if they don't exist yet
        await db.execute(text(
            f"ALTER TABLE {SCHEMA}.firms "
            "ADD COLUMN IF NOT EXISTS contact_phone TEXT, "
            "ADD COLUMN IF NOT EXISTS contact_email TEXT"
        ))
        await db.commit()
        print("Columns contact_phone / contact_email ensured.")

        for firm_name, contacts in FIRM_CONTACTS.items():
            result = await db.execute(
                update(Firm)
                .where(Firm.name == firm_name)
                .values(**contacts)
                .returning(Firm.id, Firm.name)
            )
            row = result.first()
            if row:
                print(f"Updated: {row.name} ({row.id})")
            else:
                print(f"Not found: {firm_name}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
