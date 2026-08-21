
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

# Handle asyncpg url for sync engine
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(db_url)
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        if row:
            print(f"DB_REVISION:{row[0]}")
        else:
            print("DB_REVISION:None")
    except Exception as e:
        print(f"Error: {e}")
