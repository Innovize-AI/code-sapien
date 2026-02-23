import asyncio
from sqlalchemy import text

from dotenv import load_dotenv

load_dotenv()

from db.database import engine

async def add_selling_profile_column():
    print("Checking for missing selling_profile_json column in organization_settings...")
    async with engine.begin() as conn:
        try:
            # Postgres syntax
            await conn.execute(text("ALTER TABLE organization_settings ADD COLUMN selling_profile_json TEXT"))
            print("Added selling_profile_json column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("selling_profile_json already exists.")
            else:
                print(f"Error adding selling_profile_json: {e}")

if __name__ == "__main__":
    asyncio.run(add_selling_profile_column())
