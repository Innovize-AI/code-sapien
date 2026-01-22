
import asyncio
from sqlalchemy import create_engine, inspect
from db.config import settings

def test_db():
    print(f"Connecting to database...")
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    inspector = inspect(engine)
    print(f"Tables: {inspector.get_table_names()}")
    cols = [c['name'] for c in inspector.get_columns("research_reports")]
    print(f"Columns in research_reports: {cols}")

if __name__ == "__main__":
    test_db()
