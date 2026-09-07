# RFQ Agent — Deployment Guide

## Prerequisites

- Docker installed and logged in to GCR: `gcloud auth configure-docker`
- `gcloud` CLI authenticated: `gcloud auth login`
- GCP project: `innovize-ai`
- Supabase database already running

---

## 1. Prepare Environment Variables

Copy and fill in all values in `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
DB_SCHEMA=rfq

# LLM
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
LANGCHAIN_API_KEY=...         # optional — LangSmith tracing

# Gmail IMAP (email watcher + send quotations)
GMAIL_USER=admin@innovizeai.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
GMAIL_SENDER=admin@innovizeai.com

# Email config
COMPANY_NAME=InnovizeAI
REVIEWER_EMAIL=admin@innovizeai.com

# Pub/Sub (Gmail push notifications)
PUBSUB_TOPIC=projects/innovize-ai/topics/gmail-rfq-push
PUBSUB_VERIFY_TOKEN=          # optional — leave blank to skip token check
GMAIL_WATCH_EMAIL=admin@innovizeai.com

# OAuth credentials — paste full contents of credentials.json here (single line)
GOOGLE_OAUTH_CREDENTIALS={"installed":{"client_id":"...","client_secret":"...","redirect_uris":[...]}}

# App
ENVIRONMENT=production
ALLOW_ORIGINS=https://your-frontend-url.com
BACKEND_URL=https://your-cloud-run-url.run.app
FRONTEND_URL=https://your-frontend-url.com
```

---

## 2. Build and Push Docker Image

```bash
cd demos/workflow-demos/rfq-agent/backend

docker build -t gcr.io/innovize-ai/rfq-agent-backend .
docker push gcr.io/innovize-ai/rfq-agent-backend
```

---

## 3. Deploy to Cloud Run

```bash
gcloud run deploy rfq-agent-backend \
  --image gcr.io/innovize-ai/rfq-agent-backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 1Gi \
  --cpu 1 \
  --port 8080 \
  --set-env-vars DATABASE_URL="postgresql+psycopg://..." \
  --set-env-vars ANTHROPIC_API_KEY="sk-ant-..." \
  --set-env-vars GMAIL_USER="admin@innovizeai.com" \
  --set-env-vars GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
  --set-env-vars COMPANY_NAME="InnovizeAI" \
  --set-env-vars REVIEWER_EMAIL="admin@innovizeai.com" \
  --set-env-vars PUBSUB_TOPIC="projects/innovize-ai/topics/gmail-rfq-push" \
  --set-env-vars ENVIRONMENT="production"
```

> After deploy, note the Service URL — you'll need it for the Pub/Sub push subscription.

---

## 4. Seed the Catalog (first time only)

```bash
# Run inside the container or locally pointing at the same DATABASE_URL
cd backend
python scripts/seed_catalog.py
python scripts/seed_demo.py --clear   # optional demo RFQs
```

Or exec into the running container:

```bash
gcloud run jobs execute rfq-agent-backend --region us-central1
```

---

## 5. Gmail Push Notifications via Pub/Sub

### 5a. Enable APIs in GCP

```bash
gcloud services enable gmail.googleapis.com pubsub.googleapis.com \
  --project innovize-ai
```

### 5b. Create Pub/Sub Topic

```bash
gcloud pubsub topics create gmail-rfq-push --project innovize-ai
```

### 5c. Grant Gmail Permission to Publish

```bash
gcloud pubsub topics add-iam-policy-binding gmail-rfq-push \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project innovize-ai
```

### 5d. Create Push Subscription

Replace `YOUR_CLOUD_RUN_URL` with the URL from step 3.

```bash
gcloud pubsub subscriptions create gmail-rfq-push-sub \
  --topic gmail-rfq-push \
  --push-endpoint="https://YOUR_CLOUD_RUN_URL/api/webhook/gmail" \
  --ack-deadline=60 \
  --project innovize-ai
```

### 5e. Download OAuth Credentials

1. Go to GCP Console → APIs & Services → Credentials
2. Create an OAuth 2.0 Client ID (Desktop app)
3. Download JSON → save as `backend/credentials.json`

### 5f. Register Gmail Watch

```bash
cd backend
pip install google-api-python-client google-auth-oauthlib
python scripts/setup_gmail_watch.py
```

This opens a browser for OAuth consent. After approval, a `gmail_token.json` is saved locally.

> **Watch expires every 7 days.** Re-run `setup_gmail_watch.py` weekly, or set up a Cloud Scheduler job:

```bash
gcloud scheduler jobs create http rfq-gmail-watch-refresh \
  --schedule="0 8 * * 1" \
  --uri="https://YOUR_CLOUD_RUN_URL/api/webhook/gmail/refresh-watch" \
  --http-method=POST \
  --location=us-central1 \
  --project innovize-ai
```

---

## 6. Redeploy After Code Changes

```bash
docker build -t gcr.io/innovize-ai/rfq-agent-backend .
docker push gcr.io/innovize-ai/rfq-agent-backend

gcloud run deploy rfq-agent-backend \
  --image gcr.io/innovize-ai/rfq-agent-backend \
  --region us-central1
```

Alembic migrations run automatically on container start.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/rfq/upload` | Submit RFQ via file |
| POST | `/api/rfq/text` | Submit RFQ via text |
| GET | `/api/rfq` | List all RFQs |
| GET | `/api/rfq/stats` | Dashboard stats |
| GET | `/api/rfq/{id}` | RFQ detail |
| POST | `/api/rfq/{id}/approve` | Approve and send quote |
| POST | `/api/rfq/{id}/reject` | Reject RFQ |
| GET | `/api/rfq/{id}/pdf` | Download quote PDF |
| GET | `/api/emails` | List Gmail inbox |
| POST | `/api/emails/{id}/process` | Process email as RFQ |
| GET | `/api/emails/watcher/status` | Email watcher status |
| POST | `/api/webhook/gmail` | Gmail Pub/Sub push receiver |
| POST | `/api/webhook/whatsapp` | WhatsApp webhook |
