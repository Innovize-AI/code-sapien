import asyncio
import sys
import os
# Add parent directory to path to allow importing db
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.database import SessionLocal, engine
from dotenv import load_dotenv

load_dotenv()

async def check_tables():
    print(f"Engine URL: {engine.url.render_as_string(hide_password=True)}")
    print("Checking tables using AsyncSession...")
    async with SessionLocal() as db:
        try:
            # Check if profiles table exists in information_schema
            result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables found: {tables}")
            
            if 'profiles' in tables:
                print("✅ 'profiles' table EXISTS in public schema.")
            else:
                print("❌ 'profiles' table DOES NOT EXIST in public schema.")
                
            # Check alembic_version
            try:
                result = await db.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                print(f"Current Alembic version: {version}")
            except Exception as e:
                print(f"Failed to check alembic_version: {e}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_tables())
