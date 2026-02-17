
import sys
import os

# Add parent directory to path to import db.database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from db.database import engine

async def add_selling_profile_column():
    print("Checking for selling_profile_json column in organization_settings...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE organization_settings ADD COLUMN selling_profile_json TEXT"))
            print("Added selling_profile_json column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("selling_profile_json already exists.")
            else:
                print(f"Error adding selling_profile_json: {e}")

if __name__ == "__main__":
    asyncio.run(add_selling_profile_column())
