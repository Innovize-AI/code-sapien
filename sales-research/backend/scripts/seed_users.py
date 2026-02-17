
import asyncio
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import Profile

# Load .env from root project directory (3 levels up from backend/scripts/seed_users.py)
# backend/scripts/seed_users.py -> backend/scripts -> backend -> sales-research -> code-sapien/.env ?
# Let's verify the structure:
# Workspace: /home/pavan/Innovize AI/code-sapien (contains .env)
# Script: /home/pavan/Innovize AI/code-sapien/sales-research/backend/scripts/seed_users.py
# Levels: 
# 1. scripts
# 2. backend
# 3. sales-research
# 4. code-sapien (ROOT)

current_dir = os.path.dirname(os.path.abspath(__file__))
# 1. scripts -> 2. backend -> 3. sales-research -> 4. code-sapien
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
env_path = os.path.join(root_dir, ".env")

print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

SUBABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUBABASE_URL:
    # Try finding it in parent directories if explicit path fails
    load_dotenv()
    SUBABASE_URL = os.getenv("SUPABASE_URL")
    SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUBABASE_URL or not SERVICE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    sys.exit(1)

# Helper to extract project ref if URL is pooler
if "pooler.supabase.com" in SUBABASE_URL or not SUBABASE_URL.startswith("http"):
    print(f"Detected Pooler URL or invalid scheme: {SUBABASE_URL}")
    # Try to extract from DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and "postgres." in DATABASE_URL:
        try:
            # Format: postgresql://postgres.[REF]:[PASS]@[HOST]:[PORT]/[DB]
            # Extract between 'postgres.' and ':'
            part1 = DATABASE_URL.split("postgres.")[1]
            project_ref = part1.split(":")[0]
            print(f"Extracted Project Ref: {project_ref}")
            SUBABASE_URL = f"https://{project_ref}.supabase.co"
            print(f"Constructed API URL: {SUBABASE_URL}")
        except Exception as e:
            print(f"Failed to extract project ref: {e}")
    else:
        # Fallback manual check for the specific ref seen in logs
        if "ydaxbgrofvsyqyaohopm" in SUBABASE_URL or "ydaxbgrofvsyqyaohopm" in str(os.getenv("DATABASE_URL", "")):
             SUBABASE_URL = "https://ydaxbgrofvsyqyaohopm.supabase.co"
             print(f"Using hardcoded project ref URL: {SUBABASE_URL}")

supabase: Client = create_client(SUBABASE_URL, SERVICE_KEY)

PARTNERS = [
    {"email": "jon@partner.com", "password": "securepassword123", "role": "user"},
    {"email": "pavan.kumar@innovizeai.com", "password": "adminpassword123", "role": "admin"}
]

# Quick key validation
ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
print(f"DEBUG: SERVICE_KEY length: {len(SERVICE_KEY) if SERVICE_KEY else 0}")
print(f"DEBUG: ANON_KEY length: {len(ANON_KEY) if ANON_KEY else 0}")
if SERVICE_KEY == ANON_KEY:
    print("CRITICAL: SUPABASE_SERVICE_ROLE_KEY is the same as SUPABASE_ANON_KEY. Admin tasks will fail.")

supabase: Client = create_client(SUBABASE_URL, SERVICE_KEY)

from sqlalchemy import select

async def seed_users():
    async with SessionLocal() as db:
        try:
            for p in PARTNERS:
                print(f"Processing {p['email']}...")
                
                # 1. Create Supabase User
                user_id = None
                try:
                    # Test if key can list users
                    try:
                        all_users = supabase.auth.admin.list_users()
                        print(f"  Debug: Successfully listed users. Total: {len(all_users)}")
                    except Exception as e_list:
                        print(f"  Debug: Failed to list users with service key: {e_list}")

                    res = supabase.auth.admin.create_user({
                        "email": p["email"],
                        "password": p["password"],
                        "email_confirm": True
                    })
                    user_id = res.user.id
                    print(f"  Created Supabase user: {user_id}")
                except Exception as e:
                    print(f"  Admin creation failed: {e}")
                    print(f"  Trying sign-in fallback...")
                    # Try to sign in to get ID
                    try:
                        res = supabase.auth.sign_in_with_password({
                            "email": p["email"],
                            "password": p["password"]
                        })
                        if res.user:
                             user_id = res.user.id
                             print(f"  Got ID via sign-in: {user_id}")
                    except Exception as e2:
                        print(f"  Failed to sign in: {e2}")
                        print(f"  Trying standard sign-up fallback...")
                        try:
                            # Standard sign up if allowed
                            res = supabase.auth.sign_up({
                                "email": p["email"],
                                "password": p["password"]
                            })
                            if res.user:
                                user_id = res.user.id
                                print(f"  Got ID via sign-up: {user_id}")
                        except Exception as e3:
                            print(f"  Failed to sign up: {e3}")

                if user_id:
                    # 1b. Ensure user is confirmed if we have service role access
                    try:
                        # Try Admin API first
                        supabase.auth.admin.update_user_by_id(
                            user_id, 
                            {"email_confirm": True}
                        )
                        print(f"  Confirmed user {p['email']} via Admin API")
                    except Exception as e_conf:
                        print(f"  Admin API confirmation failed: {e_conf}. Trying direct SQL...")
                        try:
                            # Direct SQL update on auth.users (requires DB permission)
                            from sqlalchemy import text
                            await db.execute(text(f"UPDATE auth.users SET email_confirmed_at = now(), updated_at = now() WHERE id = '{user_id}'"))
                            print(f"  Confirmed user {p['email']} via Direct SQL")
                        except Exception as e_sql:
                            print(f"  Direct SQL confirmation failed: {e_sql}")

                    # 2. Create Profile in DB using AsyncSession
                    result = await db.execute(select(Profile).where(Profile.id == user_id))
                    existing = result.scalars().first()
                    
                    if not existing:
                        profile = Profile(id=user_id, email=p["email"], role=p["role"])
                        db.add(profile)
                        print(f"  Created Profile for {p['email']}")
                    else:
                        existing.role = p["role"]
                        print(f"  Updated Role for {p['email']}")
                    
                    await db.commit()
                else:
                    print(f"  Could not determine User ID for {p['email']}")

        except Exception as e:
            print(f"Global Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(seed_users())
