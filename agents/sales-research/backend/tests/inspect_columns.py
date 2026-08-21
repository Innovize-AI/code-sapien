import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

from db.database import engine

async def inspect_columns():
    print(f"Connecting to: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL', '') else 'Local DB'}")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'organization_settings';"))
        columns = result.fetchall()
        print("\nColumns in 'organization_settings':")
        found = False
        for col in columns:
            print(f"- {col[0]} ({col[1]})")
            if col[0] == 'selling_profile_json':
                found = True
        
        print(f"\n'selling_profile_json' Found: {found}")

if __name__ == "__main__":
    asyncio.run(inspect_columns())
