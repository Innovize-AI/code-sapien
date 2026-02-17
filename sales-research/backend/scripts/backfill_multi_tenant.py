import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

async def backfill():
    load_dotenv("/home/pavan/Innovize AI/code-sapien/.env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return
        
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        # 1. Find primary admin
        result = await conn.execute(text("SELECT id FROM profiles WHERE role = 'admin' LIMIT 1"))
        admin = result.fetchone()
        if not admin:
            print("No admin found to backfill data.")
            return
        
        admin_id = admin[0]
        print(f"Backfilling data with Admin ID: {admin_id}")
        
        tables = [
            "research_reports",
            "competitors",
            "identified_profiles",
            "activities"
        ]
        
        for table in tables:
            res = await conn.execute(text(f"UPDATE {table} SET created_by_id = '{admin_id}' WHERE created_by_id IS NULL"))
            print(f"Updated {table}: {res.rowcount} rows affected.")
            
        # Lead submissions use rep_id
        res = await conn.execute(text(f"UPDATE lead_submissions SET rep_id = '{admin_id}' WHERE rep_id IS NULL"))
        print(f"Updated lead_submissions: {res.rowcount} rows affected.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(backfill())
