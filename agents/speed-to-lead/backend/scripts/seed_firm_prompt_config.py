"""
Seed prompt_config for existing firms.

Usage:
    poetry run python scripts/seed_firm_prompt_config.py
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

# Firm-specific prompt configs — add more firms here as needed
CONFIGS: dict[str, dict] = {
    "Aparna Constructions": {
        "contact_number":  "7095333335",
        "contact_email":   "sales@aparnaconstructions.com",
        "price_range":     "90 lakhs to 3 cr",
        "min_price":       "90 lakhs",
        "min_budget_note": "our 2BHK flats start from around 90 lakhs (Aparna Synergy)",
        "visit_hours":     "10AM–6PM, 7 days a week",
        "city":            "Hyderabad",
        "cab_coverage":    "anywhere in Hyderabad",
    },
}


async def main() -> None:
    async with SessionLocal() as db:
        # Add column if it doesn't exist yet
        await db.execute(text(
            f"ALTER TABLE {SCHEMA}.firms "
            "ADD COLUMN IF NOT EXISTS prompt_config JSONB DEFAULT '{}'::jsonb"
        ))
        await db.commit()
        print("Column prompt_config ensured.")
        for firm_name, config in CONFIGS.items():
            result = await db.execute(
                update(Firm)
                .where(Firm.name == firm_name)
                .values(prompt_config=config)
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
