
import asyncio
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import url

def check_columns():
    db_url = "postgresql://postgres.vayskszslzgapdpkhych:SZ5o7KfNALjelUrn@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = inspector.get_columns('organization_settings')
    print("Columns in organization_settings:")
    for column in columns:
        print(f"- {column['name']}")

if __name__ == "__main__":
    check_columns()
