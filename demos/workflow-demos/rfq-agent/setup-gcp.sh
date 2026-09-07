#!/usr/bin/env bash
# One-time GCP setup: APIs, Artifact Registry repo, and Secret Manager secrets.
# Run this once before your first deploy.
# Usage: GCP_PROJECT=my-project ./setup-gcp.sh

set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-asia-south1}"
REPO="rfq-agent"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "Project: $PROJECT_ID  Region: $REGION"

# ── APIs ────────────────────────────────────────────────────────────────────────
echo "▶ Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID" --quiet

# ── Artifact Registry ───────────────────────────────────────────────────────────
echo "▶ Creating Artifact Registry repo '$REPO'..."
gcloud artifacts repositories describe "$REPO" \
  --location="$REGION" --project="$PROJECT_ID" &>/dev/null \
|| gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT_ID" --quiet

# ── Secrets ─────────────────────────────────────────────────────────────────────
create_secret() {
  local name=$1 prompt=$2
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ $name already exists (skipping)"
  else
    echo -n "  Enter $prompt: "
    read -rs value; echo
    echo -n "$value" | gcloud secrets create "$name" \
      --data-file=- --project="$PROJECT_ID" --quiet
    echo "  ✓ Created $name"
  fi
}

echo "▶ Creating secrets..."
create_secret "rfq-database-url"         "PostgreSQL URL (postgresql+psycopg://user:pass@host/db)"
create_secret "rfq-google-api-key"       "Google API key (Gemini)"
create_secret "rfq-anthropic-api-key"    "Anthropic API key"
create_secret "rfq-google-oauth-creds"   "Google OAuth credentials JSON (paste full JSON)"
create_secret "rfq-gmail-sender"         "Gmail sender address"
create_secret "rfq-secret-key"           "App secret key (or press Enter to generate one)"

# ── Cloud Build trigger ─────────────────────────────────────────────────────────
echo "▶ Creating Cloud Build trigger (fires only on rfq-agent changes)..."
TRIGGER_NAME="rfq-agent-deploy"

if gcloud builds triggers describe "$TRIGGER_NAME" --project="$PROJECT_ID" &>/dev/null; then
  echo "  ✓ Trigger '$TRIGGER_NAME' already exists (skipping)"
else
  # GitHub connection must already exist in Cloud Build.
  # If not, connect it first at: console.cloud.google.com/cloud-build/triggers/connect
  gcloud builds triggers create github \
    --project="$PROJECT_ID" \
    --name="$TRIGGER_NAME" \
    --repo-owner="Innovize-AI" \
    --repo-name="code-sapien" \
    --branch-pattern="^workflow-demos$" \
    --build-config="demos/workflow-demos/rfq-agent/cloudbuild.yaml" \
    --included-files="demos/workflow-demos/rfq-agent/**" \
    --description="Deploy RFQ Agent on changes to demos/workflow-demos/rfq-agent/" \
    --quiet
  echo "  ✓ Trigger created: $TRIGGER_NAME"
fi

# ── IAM: grant Cloud Build SA access to secrets and Cloud Run ──────────────────
echo "▶ Granting IAM permissions..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for role in roles/run.admin roles/iam.serviceAccountUser roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CB_SA" --role="$role" --quiet
done

# Cloud Run SA needs to read secrets at runtime
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CR_SA" --role="roles/secretmanager.secretAccessor" --quiet

echo ""
echo ""
echo "═══════════════════════════════════════════════════"
echo "  Setup complete."
echo ""
echo "  Trigger: push to workflow-demos with changes under"
echo "    demos/workflow-demos/rfq-agent/**"
echo "  → Cloud Build auto-deploys both services."
echo ""
echo "  First deploy (manual):"
echo "  gcloud builds submit \\"
echo "    --config=demos/workflow-demos/rfq-agent/cloudbuild.yaml \\"
echo "    --project=$PROJECT_ID ."
echo "═══════════════════════════════════════════════════"
