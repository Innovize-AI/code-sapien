from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from db.config import DATABASE_URL, DB_SCHEMA

from sqlalchemy import event

_is_pooler = "pooler.supabase.com" in DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        # statement_cache_size=0 is required only for PgBouncer/Supavisor transaction-mode
        # pooler connections — it disables asyncpg prepared-statement caching. On a direct
        # Postgres connection the cache is a major win (skips parse+plan on repeat queries).
        **({"statement_cache_size": 0} if _is_pooler else {}),
        "server_settings": {
            "search_path": f'"{DB_SCHEMA}", public'
        }
    }
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

from sqlalchemy import MetaData
Base = declarative_base(metadata=MetaData())

async def get_db():
    async with SessionLocal() as session:
        yield session
