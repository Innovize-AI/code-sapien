import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.database import Base
from db.crud import get_competitors
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test():
    async with AsyncSessionLocal() as db:
        print("Fetching competitors...")
        competitors = await get_competitors(db)
        print(f"Found {len(competitors)} competitors.")
        for comp in competitors:
            creator = getattr(comp, "creator_name", "MISSING")
            print(f"ID: {comp.id} | Name: {comp.name} | Creator: {creator}")
            if creator == "MISSING" or creator is None:
                print("❌ FAILED: creator_name is missing or null.")
            else:
                print("✅ PASSED: creator_name is present.")

if __name__ == "__main__":
    asyncio.run(test())
