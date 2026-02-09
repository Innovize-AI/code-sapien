
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from db.config import DATABASE_URL

async def test_conn():
    print("Connecting to database...")
    try:
        engine = create_async_engine(DATABASE_URL)
        async with engine.connect() as conn:
            print("Successfully connected!")
            result = await conn.execute("SELECT 1")
            print(f"Result: {result.fetchone()}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
