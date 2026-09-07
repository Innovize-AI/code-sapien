"""
One-time setup: register Gmail push notifications via Google Pub/Sub.

Run once (and again every 7 days — watch expires):
    python scripts/setup_gmail_watch.py

Prerequisites:
1. GCP project with Gmail API + Pub/Sub API enabled.
2. A Pub/Sub topic, e.g. projects/YOUR_PROJECT/topics/gmail-rfq-push
3. Grant gmail-api-push@system.gserviceaccount.com the "Pub/Sub Publisher" role on that topic.
4. A push subscription on the topic pointing to:
       https://YOUR_BACKEND_URL/api/webhook/gmail
5. OAuth credentials (credentials.json) OR a service account JSON.
   - Download credentials.json from GCP Console -> APIs & Services -> Credentials
   - Place it at backend/credentials.json

ENV vars required (can be in .env):
    GMAIL_WATCH_EMAIL      — Gmail address to watch (default: GMAIL_USER)
    PUBSUB_TOPIC           — full topic name, e.g. projects/my-project/topics/gmail-rfq-push
    GOOGLE_CREDENTIALS     — path to credentials.json (default: ./credentials.json)
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load env
_wf_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_wf_env)
_local_env = Path(__file__).resolve().parent.parent / ".env"
if _local_env.exists():
    load_dotenv(_local_env, override=True)

EMAIL  = os.getenv("GMAIL_WATCH_EMAIL") or os.getenv("GMAIL_USER", "")
TOPIC  = os.getenv("PUBSUB_TOPIC", "")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_credentials():
    import json as _json
    from google_auth_oauthlib.flow import InstalledAppFlow

    raw = os.getenv("GOOGLE_OAUTH_CREDENTIALS", "")
    if not raw:
        print("ERROR: GOOGLE_OAUTH_CREDENTIALS env var not set.")
        print("Paste the full contents of your credentials.json into this variable.")
        sys.exit(1)

    client_config = _json.loads(raw)
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    print("OAuth consent complete.")
    return creds


def main():
    if not EMAIL:
        print("ERROR: set GMAIL_WATCH_EMAIL or GMAIL_USER in .env")
        sys.exit(1)
    if not TOPIC:
        print("ERROR: set PUBSUB_TOPIC in .env, e.g. projects/my-project/topics/gmail-rfq-push")
        sys.exit(1)

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: install google-api-python-client and google-auth-oauthlib:")
        print("  pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    body = {
        "topicName": TOPIC,
        "labelIds": ["INBOX"],
        "labelFilterBehavior": "INCLUDE",
    }

    result = service.users().watch(userId=EMAIL, body=body).execute()
    print(f"Gmail watch registered:")
    print(f"  historyId : {result.get('historyId')}")
    print(f"  expiration: {result.get('expiration')} ms epoch")
    print()
    print("Gmail will now push to your Pub/Sub topic on every new INBOX email.")
    print("Watch expires in ~7 days — re-run this script (or schedule it weekly).")


if __name__ == "__main__":
    main()
