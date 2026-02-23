import asyncio
from sqlalchemy import text
from db.database import engine

async def fix_revision():
    async with engine.begin() as conn:
        try:
            # First, check if the table exists
            await conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
            
            # Check current value
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            
            if row:
                print(f"Current revision in DB: {row[0]}")
                await conn.execute(text("UPDATE alembic_version SET version_num = '913e2401f88e'"))
                print("Updated revision to 913e2401f88e")
            else:
                print("No revision found. Inserting 913e2401f88e")
                await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('913e2401f88e')"))
        except Exception as e:
            print(f"Error fixing revision: {e}")

if __name__ == "__main__":
    asyncio.run(fix_revision())
