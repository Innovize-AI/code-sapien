
import sys
import os

# Add parent directory to path to import db.database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from db.database import engine

async def add_slack_user_id_column():
    print("Checking for slack_user_id column in user_settings...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN slack_user_id VARCHAR"))
            print("Added slack_user_id column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("slack_user_id already exists.")
            else:
                print(f"Error adding slack_user_id: {e}")

        # Add unique constraint separately (SQLite doesn't support adding constraint in ADD COLUMN usually, specific based on DB)
        # Postgres does. But let's keep it simple first.
        # Actually sqlalchemy 'unique=True' in model implies a constraint.
        # Ideally we add a unique index.
        try:
             await conn.execute(text("CREATE UNIQUE INDEX idx_user_settings_slack_user_id ON user_settings (slack_user_id)"))
             print("Added unique index for slack_user_id.")
        except Exception as e:
             if "already exists" in str(e).lower():
                 print("Index already exists.")
             else:
                 print(f"Error creating index: {e}")

if __name__ == "__main__":
    asyncio.run(add_slack_user_id_column())
