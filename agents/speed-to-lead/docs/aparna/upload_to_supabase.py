"""
Upload Aparna brochure PDFs to Supabase Storage (resources bucket).
Prints public URLs to update resources.json.

Run from this directory:
    python upload_to_supabase.py
"""

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

# The Supabase URL and service-role key come from backend/.env (or the environment).
# Never paste the key into this file: it is a full admin key and would end up in git.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "resources"

FILES = [
    ("cyberzed-brochure.pdf",   "aparna/cyberzed-brochure.pdf"),
    ("moonstone-brochure.pdf",  "aparna/moonstone-brochure.pdf"),
    ("newlands-brochure.pdf",   "aparna/newlands-brochure.pdf"),
    ("synergy-brochure.pdf",    "aparna/synergy-brochure.pdf"),
    ("payment-plan-guide.pdf",  "aparna/payment-plan-guide.pdf"),
]

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env first.")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"Uploading to Supabase bucket: {BUCKET}\n")

    # Create bucket if it doesn't exist
    try:
        sb.storage.create_bucket(BUCKET, options={"public": True})
        print(f"Created bucket: {BUCKET}\n")
    except Exception as e:
        if "already exists" in str(e).lower() or "Duplicate" in str(e):
            print(f"Bucket already exists: {BUCKET}\n")
        else:
            print(f"Bucket note: {e}\n")

    results = {}
    for local_name, storage_path in FILES:
        if not os.path.exists(local_name):
            print(f"  SKIP: {local_name} not found")
            continue

        with open(local_name, "rb") as f:
            data = f.read()

        try:
            # Remove existing file if present (upsert)
            sb.storage.from_(BUCKET).remove([storage_path])
        except Exception:
            pass

        sb.storage.from_(BUCKET).upload(
            storage_path, data,
            {"content-type": "application/pdf", "upsert": "true"},
        )
        url = sb.storage.from_(BUCKET).get_public_url(storage_path)
        results[local_name] = url
        print(f"  {local_name}")
        print(f"  → {url}\n")

    print("\n--- resources.json url values ---")
    for local_name, url in results.items():
        print(f'"{local_name}": "{url}"')

if __name__ == "__main__":
    main()
