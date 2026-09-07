# RFQ Agent — Deployment Guide

Everything deploys through Cloud Build. After one-time GCP setup, every push to the
`workflow-demos` branch that touches `demos/workflow-demos/rfq-agent/**` triggers a
full backend + frontend deploy automatically.

---

## Prerequisites

- `gcloud` CLI installed and authenticated: `gcloud auth login`
- GCP project created and billing enabled
- GitHub repo connected to Cloud Build (one-time, done in GCP Console)
- `.env` files present locally (values are read by `setup-gcp.sh`):
  - `demos/workflow-demos/.env` — shared keys
  - `demos/workflow-demos/rfq-agent/backend/.env` — rfq-specific keys

---

## Step 1 — One-time GCP setup

Run from the repo root:

```bash
GCP_PROJECT=your-project-id ./demos/workflow-demos/rfq-agent/setup-gcp.sh
```

This script:
- Enables Cloud Run, Artifact Registry, Cloud Build, Secret Manager, Pub/Sub APIs
- Creates the `rfq-agent` Artifact Registry Docker repo
- Reads your `.env` files and pushes these secrets to Secret Manager:

| Secret Manager name      | Env var                   | Required |
|--------------------------|---------------------------|----------|
| `rfq-database-url`       | `DATABASE_URL`            | yes |
| `rfq-google-api-key`     | `GOOGLE_API_KEY`          | yes |
| `rfq-anthropic-api-key`  | `ANTHROPIC_API_KEY`       | yes |
| `rfq-google-oauth-creds` | `GOOGLE_OAUTH_CREDENTIALS`| yes |
| `rfq-gmail-sender`       | `GMAIL_USER`              | yes |
| `rfq-gmail-password`     | `GMAIL_PASSWORD`          | yes |
| `rfq-langchain-api-key`  | `LANGCHAIN_API_KEY`       | optional |
| `rfq-slack-webhook`      | `SLACK_WEBHOOK_URL`       | optional |
| `rfq-pubsub-verify-token`| `PUBSUB_VERIFY_TOKEN`     | optional |

- Creates the `rfq-gmail-push` Pub/Sub topic and grants Gmail SA publish permission
- Creates a Cloud Build trigger scoped to `demos/workflow-demos/rfq-agent/**` on the `workflow-demos` branch
- Grants Cloud Build and Cloud Run service accounts the required IAM roles

> Safe to re-run — skips anything already created. Resume from a step with `--from <step>`.
> Steps: `env` | `apis` | `artifact-registry` | `secrets` | `pubsub` | `trigger` | `iam`

---

## Step 2 — Connect GitHub to Cloud Build (if not done)

```
https://console.cloud.google.com/cloud-build/triggers/connect
```

Connect the `Innovize-AI/code-sapien` repository. The trigger created in Step 1 activates on pushes.

---

## Step 3 — First deploy

Push your branch, or trigger manually from the repo root:

```bash
gcloud builds submit \
  --config=demos/workflow-demos/rfq-agent/cloudbuild.yaml \
  --project=your-project-id \
  .
```

### What Cloud Build does (8 steps):

```
1. build-backend   → docker build backend image
2. push-backend    → push to Artifact Registry (asia-south1)
3. deploy-backend  → gcloud run deploy rfq-backend in us-central1 (injects all secrets)
4. get-backend-url → capture live backend URL → /workspace/backend_url.txt
5. setup-pubsub    → create or update Pub/Sub push subscription → backend /api/webhook/gmail
6. build-frontend  → docker build frontend (bakes backend URL in at build time)
7. push-frontend   → push to Artifact Registry
8. deploy-frontend → gcloud run deploy rfq-frontend in us-central1
```

Alembic migrations run automatically on backend container start.

---

## Step 4 — Map subdomain (one-time, after first deploy)

```bash
GCP_PROJECT=your-project-id ./demos/workflow-demos/setup-domains.sh
```

Add the CNAME record it prints at your DNS provider:

```
rfq.demos.innovizeai.com  →  ghs.googlehosted.com
```

SSL provisions automatically within ~15 minutes.

---

## Step 5 — Patch CORS (one-time, after domain is mapped)

```bash
FRONTEND_CR_URL=$(gcloud run services describe rfq-frontend \
  --region=us-central1 --format="value(status.url)" --project=your-project-id)

gcloud run services update rfq-backend \
  --region=us-central1 \
  --update-env-vars="ALLOW_ORIGINS=https://rfq.demos.innovizeai.com,$FRONTEND_CR_URL" \
  --project=your-project-id
```

Both URLs are allowed — custom domain for production, Cloud Run URL as fallback during DNS propagation.

---

## Step 6 — Seed the catalog (first time only)

```bash
cd demos/workflow-demos/rfq-agent/backend
python scripts/seed_catalog.py
python scripts/seed_demo.py --clear   # optional demo data
```

---

## Step 7 — Connect Gmail (one-time, after first deploy)

The Pub/Sub topic and push subscription are wired automatically by Cloud Build.
What you do once manually:

**1. Add OAuth credentials** — GCP Console → APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop app). Download JSON, paste full contents as `GOOGLE_OAUTH_CREDENTIALS` in `.env`, then update the secret:

```bash
echo -n '{"installed":{...}}' | gcloud secrets versions add rfq-google-oauth-creds \
  --data-file=- --project=your-project-id
```

**2. Connect Gmail account** — open the deployed app → Settings → Connect Gmail. This saves the OAuth token to the database.

> Gmail watch expires every 7 days. Schedule a weekly refresh:

```bash
gcloud scheduler jobs create http rfq-gmail-watch-refresh \
  --schedule="0 8 * * 1" \
  --uri="https://rfq.demos.innovizeai.com/api/webhook/gmail/refresh-watch" \
  --http-method=POST \
  --location=us-central1 \
  --project=your-project-id
```

---

## Subsequent deploys (automatic)

Push changes to the `workflow-demos` branch:

```bash
git push origin workflow-demos
```

Cloud Build fires automatically if any file under `demos/workflow-demos/rfq-agent/**` changed.

---

## Updating a secret

```bash
echo -n "new-value" | gcloud secrets versions add rfq-<name> \
  --data-file=- --project=your-project-id
```

Redeploy to pick up the new version (Cloud Build always pulls `:latest`).

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | `https://rfq.demos.innovizeai.com` |
| Frontend (Cloud Run) | printed at end of Cloud Build |
| Backend (Cloud Run) | printed at end of Cloud Build |
| Health check | `GET /health` |

---

## API Reference

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
