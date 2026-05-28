from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from db.config import DATABASE_URL, DB_SCHEMA

from sqlalchemy import event

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    connect_args={
        "statement_cache_size": 0,
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
