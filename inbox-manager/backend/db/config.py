import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres.vayskszslzgapdpkhych:SZ5o7KfNALjelUrn@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
)
