"""
Create a Supabase Auth user for the Saarthi dashboard.

Uses the Supabase Admin API (service role key) — this bypasses email
confirmation so the user can log in immediately.

Usage:
    poetry run python scripts/seed_admin_user.py \
        --email admin@dwpshyd.in \
        --password SecurePassword123 \
        --name "Admissions Admin" \
        --role admin

    poetry run python scripts/seed_admin_user.py \
        --email priya@dwpshyd.in \
        --password SecurePassword123 \
        --name "Priya Sharma" \
        --role counselor

Roles:
    admin      — full access (pause AI, reply, broadcast, view all)
    counselor  — takeover + reply, no broadcast
    viewer     — read-only (analytics + conversations)
"""

import argparse
import sys
from dotenv import load_dotenv

load_dotenv()

from config import settings
from supabase import create_client, Client


VALID_ROLES = ("admin", "counselor", "viewer")


def create_user(email: str, password: str, name: str, role: str) -> None:
    if role not in VALID_ROLES:
        print(f"❌ Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}")
        sys.exit(1)

    sb: Client = create_client(settings.supabase_url, settings.supabase_service_key)

    print(f"Creating user: {email} | role={role} | name={name}")

    # Create user via admin API — email_confirm=True skips confirmation email
    response = sb.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "name": name,
            "role": role,
            "org": "dwps",
            "permissions": _permissions_for(role),
        },
    })

    user = response.user
    if not user:
        print(f"❌ Failed to create user: {response}")
        sys.exit(1)

    print(f"✅ User created successfully")
    print(f"   ID:    {user.id}")
    print(f"   Email: {user.email}")
    print(f"   Role:  {role}")
    print(f"   Name:  {name}")
    print()
    print("The user can now log in at the Saarthi dashboard.")


def _permissions_for(role: str) -> dict:
    """Return module permissions dict for the given role."""
    if role == "admin":
        return {
            "saarthi": ["read", "takeover", "reply", "broadcast"],
        }
    if role == "counselor":
        return {
            "saarthi": ["read", "takeover", "reply"],
        }
    # viewer
    return {
        "saarthi": ["read"],
    }


def list_users() -> None:
    sb: Client = create_client(settings.supabase_url, settings.supabase_service_key)
    response = sb.auth.admin.list_users()
    users = response if isinstance(response, list) else getattr(response, "users", [])

    if not users:
        print("No users found.")
        return

    print(f"{'Email':<35} {'Name':<20} {'Role':<12} {'ID'}")
    print("-" * 90)
    for u in users:
        meta = u.user_metadata or {}
        print(f"{u.email:<35} {meta.get('name', '—'):<20} {meta.get('role', '—'):<12} {u.id}")


def delete_user(email: str) -> None:
    sb: Client = create_client(settings.supabase_url, settings.supabase_service_key)
    response = sb.auth.admin.list_users()
    users = response if isinstance(response, list) else getattr(response, "users", [])

    user = next((u for u in users if u.email == email), None)
    if not user:
        print(f"❌ User not found: {email}")
        sys.exit(1)

    sb.auth.admin.delete_user(user.id)
    print(f"✅ Deleted user: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Saarthi dashboard users")
    subparsers = parser.add_subparsers(dest="command")

    # create
    create_p = subparsers.add_parser("create", help="Create a new user")
    create_p.add_argument("--email",    required=True)
    create_p.add_argument("--password", required=True)
    create_p.add_argument("--name",     required=True)
    create_p.add_argument("--role",     default="viewer", choices=VALID_ROLES)

    # list
    subparsers.add_parser("list", help="List all users")

    # delete
    delete_p = subparsers.add_parser("delete", help="Delete a user")
    delete_p.add_argument("--email", required=True)

    args = parser.parse_args()

    if args.command == "create":
        create_user(args.email, args.password, args.name, args.role)
    elif args.command == "list":
        list_users()
    elif args.command == "delete":
        delete_user(args.email)
    else:
        # Default: create with positional-style args for convenience
        parser.print_help()
