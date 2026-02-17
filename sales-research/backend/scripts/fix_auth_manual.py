import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

async def fix_user():
    # Force absolute path to .env
    load_dotenv("/home/pavan/Innovize AI/code-sapien/.env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found")
        return
        
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    
    email = "pavan.kumar@innovizeai.com"
    
    try:
        async with engine.begin() as conn:
            print(f"Fixing user: {email}")
            result = await conn.execute(text(f"UPDATE auth.users SET email_confirmed_at = now(), updated_at = now() WHERE email = '{email}'"))
            print(f"Update result: {result.rowcount} rows affected.")
    except Exception as e:
        print(f"Failed to update user: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_user())
