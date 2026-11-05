from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData

from db.config import DATABASE_URL, SCHEMA

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "options": f'-c search_path="{SCHEMA}",public',
        "prepare_threshold": None,  # disable prepared statements for PgBouncer transaction pooling
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base(metadata=MetaData(schema=SCHEMA))


async def get_db():
    async with SessionLocal() as session:
        yield session
