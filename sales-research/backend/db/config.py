import os
from dotenv import load_dotenv

# Search for .env in current and parent directories
def load_project_dotenv():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Try current dir (backend/db), parent (backend), and grandparent (sales-research), then root (code-sapien)
    search_dirs = [
        current_dir,
        os.path.dirname(current_dir),
        os.path.dirname(os.path.dirname(current_dir)),
        os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    ]
    for d in search_dirs:
        env_path = os.path.join(d, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return True
    return False

load_project_dotenv()

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
    
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")
