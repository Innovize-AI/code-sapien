from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from db.config import DATABASE_URL, DB_SCHEMA

from sqlalchemy import event

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=5,
    max_overflow=0,
    connect_args={
        "statement_cache_size": 0,
        "server_settings": {
            "search_path": f'"{DB_SCHEMA}"'
        }
    }
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
