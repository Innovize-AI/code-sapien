"""
Delete all simulation leads (+SIM*) and their cascaded data:
sessions, conversation_logs, retrieval_logs, visits, profiles, followups.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from sqlalchemy import delete, select
from db.database import SessionLocal
from db.models import Lead


async def main() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(Lead.id, Lead.phone).where(Lead.phone.like("+SIM%"))
        )
        rows = result.all()

        if not rows:
            print("No simulation leads found.")
            return

        print(f"Found {len(rows)} simulation lead(s):")
        for row in rows:
            print(f"  {row.phone}  ({row.id})")

        await db.execute(delete(Lead).where(Lead.phone.like("+SIM%")))
        await db.commit()
        print(f"\nDeleted {len(rows)} lead(s) and all cascaded data.")


if __name__ == "__main__":
    asyncio.run(main())
