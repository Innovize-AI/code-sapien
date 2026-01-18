import asyncio
from sqlalchemy import text
from db.database import engine

async def check_revision():
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            if row:
                print(f"Current revision in DB: {row[0]}")
            else:
                print("No revision found in alembic_version table.")
        except Exception as e:
            print(f"Error checking revision: {e}")

if __name__ == "__main__":
    asyncio.run(check_revision())
