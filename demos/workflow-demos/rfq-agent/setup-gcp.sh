#!/usr/bin/env bash
# One-time GCP setup: APIs, Artifact Registry repo, and Secret Manager secrets.
# Run this once before your first deploy. Safe to re-run — skips completed steps.
#
# Reads secret values from .env files automatically:
#   demos/workflow-demos/.env          — shared keys (DATABASE_URL, API keys, GMAIL_USER…)
#   demos/workflow-demos/rfq-agent/backend/.env  — rfq-specific (GOOGLE_OAUTH_CREDENTIALS…)
#
# Usage:
#   GCP_PROJECT=my-project ./setup-gcp.sh              # run all steps
#   GCP_PROJECT=my-project ./setup-gcp.sh --from iam   # resume from a specific step
#
# Steps: env | apis | artifact-registry | secrets | pubsub | trigger | iam

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
REPO="rfq-agent"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

# ── Step control ────────────────────────────────────────────────────────────────
STEPS=(env apis artifact-registry secrets pubsub trigger iam)
FROM_STEP="${FROM_STEP:-}"

# Allow --from <step> as a CLI argument
if [[ "${1:-}" == "--from" && -n "${2:-}" ]]; then
  FROM_STEP="$2"
fi

_skip=false
[[ -n "$FROM_STEP" ]] && _skip=true

should_run() {
  local step=$1
  if $_skip; then
    if [[ "$step" == "$FROM_STEP" ]]; then
      _skip=false   # found the resume point — run from here
    else
      echo "⏭  Skipping: $step"
      return 1
    fi
  fi
  return 0
}

echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
[[ -n "$FROM_STEP" ]] && echo "Resuming from: $FROM_STEP"
echo ""

# ── Step: env ──────────────────────────────────────────────────────────────────
if should_run "env"; then
  load_env() {
    local file=$1
    if [[ ! -f "$file" ]]; then
      echo "  (not found: $file)"
      return
    fi
    echo "  Loading $file"
    while IFS= read -r line; do
      line="${line//$'\r'/}"
      [[ "$line" =~ ^\s*# ]] && continue
      [[ -z "${line//[[:space:]]/}" ]] && continue
      [[ "$line" != *=* ]] && continue
      key="${line%%=*}"
      value="${line#*=}"
      key="${key// /}"
      if [[ "$value" =~ ^\"(.*)\"$ ]]; then value="${BASH_REMATCH[1]}"; fi
      if [[ "$value" =~ ^\'(.*)\'$ ]]; then value="${BASH_REMATCH[1]}"; fi
      export "$key=$value"
    done < "$file"
  }

  echo "▶ [env] Loading .env files..."
  load_env "$REPO_ROOT/demos/workflow-demos/.env"
  load_env "$SCRIPT_DIR/backend/.env"
fi

# ── Step: apis ─────────────────────────────────────────────────────────────────
if should_run "apis"; then
  echo "▶ [apis] Enabling GCP APIs..."
  gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    pubsub.googleapis.com \
    gmail.googleapis.com \
    --project="$PROJECT_ID" --quiet
  echo "  ✓ APIs enabled"
fi

# ── Step: artifact-registry ────────────────────────────────────────────────────
if should_run "artifact-registry"; then
  echo "▶ [artifact-registry] Creating Artifact Registry repo '$REPO'..."
  if gcloud artifacts repositories describe "$REPO" \
       --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ Already exists (skipping)"
  else
    gcloud artifacts repositories create "$REPO" \
      --repository-format=docker \
      --location="$REGION" \
      --project="$PROJECT_ID" --quiet
    echo "  ✓ Created: $REPO"
  fi
fi

# ── Step: secrets ──────────────────────────────────────────────────────────────
if should_run "secrets"; then
  push_secret() {
    local name=$1 env_var=$2 prompt=$3 optional=${4:-required}
    local value="${!env_var:-}"

    if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
      echo "  ✓ $name already exists (skipping)"
      return 0
    fi

    if [[ -z "$value" ]]; then
      echo -n "  $env_var not set — enter $prompt: "
      read -rs value; echo
    else
      echo "  Using \$$env_var → $name"
    fi

    if [[ -z "$value" ]]; then
      if [[ "$optional" == "optional" ]]; then
        echo "  (skipping optional $name)"
        return 0
      fi
      echo "  ERROR: no value for $name"
      return 1
    fi

    echo -n "$value" | gcloud secrets create "$name" \
      --data-file=- --project="$PROJECT_ID" --quiet
    echo "  ✓ Created $name"
  }

  echo "▶ [secrets] Creating secrets..."
  push_secret "rfq-database-url"        "DATABASE_URL"             "PostgreSQL URL"
  push_secret "rfq-google-api-key"      "GOOGLE_API_KEY"           "Google API key (Gemini)"
  push_secret "rfq-anthropic-api-key"   "ANTHROPIC_API_KEY"        "Anthropic API key"
  push_secret "rfq-google-oauth-creds"  "GOOGLE_OAUTH_CREDENTIALS" "Google OAuth credentials JSON"
  push_secret "rfq-gmail-sender"        "GMAIL_USER"               "Gmail sender address"
  push_secret "rfq-gmail-password"      "GMAIL_PASSWORD"           "Gmail app password"
  push_secret "rfq-langchain-api-key"   "LANGCHAIN_API_KEY"        "LangSmith API key"        optional
  push_secret "rfq-slack-webhook"       "SLACK_WEBHOOK_URL"        "Slack webhook URL"        optional
  push_secret "rfq-pubsub-verify-token" "PUBSUB_VERIFY_TOKEN"      "Pub/Sub verify token"     optional
fi

# ── Step: pubsub ───────────────────────────────────────────────────────────────
if should_run "pubsub"; then
  PUBSUB_TOPIC="rfq-gmail-push"
  echo "▶ [pubsub] Creating Pub/Sub topic '$PUBSUB_TOPIC'..."
  if gcloud pubsub topics describe "$PUBSUB_TOPIC" --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ Topic already exists (skipping)"
  else
    gcloud pubsub topics create "$PUBSUB_TOPIC" --project="$PROJECT_ID" --quiet
    echo "  ✓ Created topic: $PUBSUB_TOPIC"
  fi

  echo "  Granting Gmail SA publish permission..."
  gcloud pubsub topics add-iam-policy-binding "$PUBSUB_TOPIC" \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher" \
    --condition=None \
    --project="$PROJECT_ID" --quiet
  echo "  ✓ Gmail SA can publish to $PUBSUB_TOPIC"
fi

# ── Step: trigger ──────────────────────────────────────────────────────────────
if should_run "trigger"; then
  TRIGGER_NAME="rfq-agent-deploy"
  echo "▶ [trigger] Creating Cloud Build trigger..."
  if gcloud builds triggers describe "$TRIGGER_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ Trigger '$TRIGGER_NAME' already exists (skipping)"
  else
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
fi

# ── Step: iam ──────────────────────────────────────────────────────────────────
if should_run "iam"; then
  echo "▶ [iam] Granting IAM permissions..."
  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
  CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
  CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

  for role in roles/run.admin roles/iam.serviceAccountUser roles/secretmanager.secretAccessor roles/pubsub.editor; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$CB_SA" --role="$role" --condition=None --quiet
    echo "  ✓ $role → Cloud Build SA"
  done

  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CR_SA" --role="roles/secretmanager.secretAccessor" --condition=None --quiet
  echo "  ✓ roles/secretmanager.secretAccessor → Cloud Run SA"
fi

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
