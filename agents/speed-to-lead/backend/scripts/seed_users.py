"""
Seed Supabase Auth users for Speed-to-Lead.

Users created:
  admin@speedtolead.ai          — super admin, no firm_id (sees all firms)
  interior@speedtolead.ai       — counselor for Studio Luxe Interiors
  realestate@speedtolead.ai     — counselor for Prestige Homes
  solar@speedtolead.ai          — counselor for Greenfield Solar

All passwords: SeedPass@123  (change after first login)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import requests

SUPABASE_URL     = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

HEADERS = {
    "apikey":        SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type":  "application/json",
}

FIRM_IDS = {
    "interior":    "7f6d92b4-d266-4313-a91d-0b349f5e89ba",
    "real_estate": "52be1cba-b8d7-4915-a465-564fe90ca667",
    "solar":       "fa908f84-5633-4fde-95c0-957e72181b68",
}

USERS = [
    {
        "email":    "admin@speedtolead.ai",
        "password": "SeedPass@123",
        "user_metadata": {
            "name":    "Super Admin",
            "role":    "admin",
            "firm_id": None,
        },
    },
    {
        "email":    "interior@speedtolead.ai",
        "password": "SeedPass@123",
        "user_metadata": {
            "name":    "Interior Counselor",
            "role":    "counselor",
            "firm_id": FIRM_IDS["interior"],
        },
    },
    {
        "email":    "realestate@speedtolead.ai",
        "password": "SeedPass@123",
        "user_metadata": {
            "name":    "RE Counselor",
            "role":    "counselor",
            "firm_id": FIRM_IDS["real_estate"],
        },
    },
    {
        "email":    "solar@speedtolead.ai",
        "password": "SeedPass@123",
        "user_metadata": {
            "name":    "Solar Counselor",
            "role":    "counselor",
            "firm_id": FIRM_IDS["solar"],
        },
    },
]


def create_or_update_user(user: dict) -> None:
    email = user["email"]

    # Check if user already exists
    res = requests.get(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=HEADERS,
        params={"filter": f"email.eq.{email}"},
    )
    existing = [u for u in res.json().get("users", []) if u.get("email") == email]

    if existing:
        uid = existing[0]["id"]
        # Update metadata and password
        res = requests.put(
            f"{SUPABASE_URL}/auth/v1/admin/users/{uid}",
            headers=HEADERS,
            json={
                "password":      user["password"],
                "user_metadata": user["user_metadata"],
            },
        )
        if res.ok:
            print(f"  Updated : {email}")
        else:
            print(f"  ERROR updating {email}: {res.text}")
    else:
        res = requests.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=HEADERS,
            json={
                "email":            email,
                "password":         user["password"],
                "email_confirm":    True,
                "user_metadata":    user["user_metadata"],
            },
        )
        if res.ok:
            print(f"  Created : {email}")
        else:
            print(f"  ERROR creating {email}: {res.text}")


if __name__ == "__main__":
    print("Seeding users...\n")
    for u in USERS:
        create_or_update_user(u)

    print("\nDone. Credentials:")
    print("  Email                        Password       Role")
    print("  ─────────────────────────────────────────────────────")
    for u in USERS:
        role = u["user_metadata"]["role"]
        firm = u["user_metadata"].get("firm_id", "—") or "all firms"
        print(f"  {u['email']:<30} SeedPass@123   {role}")
