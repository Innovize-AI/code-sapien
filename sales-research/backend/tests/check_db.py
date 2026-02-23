import asyncio
from sqlalchemy import inspect
from db.database import engine

async def check_columns():
    async with engine.connect() as conn:
        def get_cols(target_conn):
            inspector = inspect(target_conn)
            return {table: [c['name'] for c in inspector.get_columns(table)] for table in inspector.get_table_names()}
        
        tables = await conn.run_sync(get_cols)
        print("Competitors columns:", tables.get('competitors'))
        print("IdentifiedProfiles columns:", tables.get('identified_profiles'))

if __name__ == "__main__":
    asyncio.run(check_columns())
