from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to allow importing models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import Base
from db.models import ResearchReport, OrganizationSettings, CompetitorAnalysis, Competitor, IdentifiedProfile, Profile
from db.config import DB_SCHEMA

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Overwrite the sqlalchemy.url in the config object with the one from the environment
url = os.environ.get("DATABASE_URL")
if url:
    url = url.strip().strip('"').strip("'")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    
    section = config.config_ini_section
    config.set_section_option(section, "sqlalchemy.url", url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=DB_SCHEMA,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    print(f"DEBUG: Running migrations online for schema: {DB_SCHEMA}")
    print(f"DEBUG: DATABASE_URL (masked): {config.get_main_option('sqlalchemy.url')[:20]}...")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        print(f"DEBUG: Setting search_path to {DB_SCHEMA}")
        connection.execute(text(f'SET search_path TO "{DB_SCHEMA}"'))
        
        # Ensure the schema exists
        print(f"DEBUG: Creating schema {DB_SCHEMA} if not exists")
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"'))
        
        # Commit schema creation if the dialect doesn't support transactional DDL
        # In Postgres it's transactional, but explicit commit here helps visibility
        connection.commit() 
        
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            version_table_schema=DB_SCHEMA,
            include_schemas=False,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
