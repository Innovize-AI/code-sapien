from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData

from db.config import DATABASE_URL, DB_SCHEMA

# psycopg3 (psycopg[binary]) — no prepared-statement issues with PgBouncer.
# search_path scopes all queries to the rfq schema automatically.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={
        "options": f"-c search_path={DB_SCHEMA},public"
    }
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base(metadata=MetaData())


async def get_db():
    async with SessionLocal() as session:
        yield session
