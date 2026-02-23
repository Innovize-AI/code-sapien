import os
import json
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

# Search for .env in parent directories
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(db_url)
inspector = inspect(engine)

tables = inspector.get_table_names()
print(f"TABLES found: {tables}")

if "identified_profiles" in tables:
    print("\nColumns in 'identified_profiles':")
    columns = inspector.get_columns("identified_profiles")
    for col in columns:
        print(f" - {col['name']}: {col['type']}")
else:
    print("\nERROR: 'identified_profiles' table NOT found!")
