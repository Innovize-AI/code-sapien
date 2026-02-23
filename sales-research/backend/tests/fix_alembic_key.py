
import asyncio
from sqlalchemy import text
from db.database import engine

async def fix_alembic():
    async with engine.begin() as conn:
        try:
            # Check current version
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            if row:
                current_ver = row[0]
                print(f"Current version in DB: {current_ver}")
                if current_ver == '2c20b9318e35':
                    # Update to a valid version (the parent of what we want to add)
                    # or just to the current head file that exists.
                    # Based on my check, 913e2401f88e should be the parent of the broken chain.
                    await conn.execute(text("UPDATE alembic_version SET version_num = '913e2401f88e'"))
                    print("Updated alembic_version to 913e2401f88e")
                else:
                    print("Version is not 2c20b9318e35, no manual update needed.")
            else:
                print("No version found in alembic_version.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_alembic())
