
import asyncio
from sqlalchemy import text
from db.database import engine

async def add_missing_columns():
    print("Checking for missing LinkedIn columns in organization_settings...")
    async with engine.begin() as conn:
        # Check if columns exist (using metadata or simple query)
        # SQLite doesn't support 'IF NOT EXISTS' for ADD COLUMN directly in some versions, 
        # but we can try and catch the error or check PRAGMA.
        # Since we're likely on SQLite or Postgres, we'll try a generic approach.
        
        try:
            await conn.execute(text("ALTER TABLE organization_settings ADD COLUMN user_linkedin_url TEXT"))
            print("Added user_linkedin_url column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("user_linkedin_url already exists.")
            else:
                print(f"Error adding user_linkedin_url: {e}")

        try:
            await conn.execute(text("ALTER TABLE organization_settings ADD COLUMN company_linkedin_url TEXT"))
            print("Added company_linkedin_url column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("company_linkedin_url already exists.")
            else:
                print(f"Error adding company_linkedin_url: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
