import os

raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres.vayskszslzgapdpkhych:SZ5o7KfNALjelUrn@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
)

# Ensure the URL is compatible with asyncpg
if raw_url.startswith("postgres://"):
    DATABASE_URL = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgresql://"):
    DATABASE_URL = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_url
