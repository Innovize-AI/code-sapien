#!/usr/bin/env bash
# This script needs bash. If it was started with sh (dash) or another shell, stop with a clear message
# before any bash-only syntax is read. Start it with:  bash setup-gcp.sh
if [ -z "${BASH_VERSION:-}" ]; then
  echo "ERROR: run this script with bash, not sh:  bash setup-gcp.sh"
  exit 1
fi
# One-time GCP setup for Speed to Lead: APIs, Artifact Registry repo, Secret Manager secrets,
# the Cloud Build trigger, and IAM. Safe to re-run: it skips what already exists.
# Modelled on demos/workflow-demos/rfq-agent/setup-gcp.sh.
#
# Secret values are read from backend/.env, so nothing is typed on the command line:
#   agents/speed-to-lead/backend/.env
# A value that is missing is asked for with hidden input. Optional ones can be left empty and get a
# placeholder, because Cloud Run needs every mounted secret to exist.
#
# Usage (run from anywhere):
#   GCP_PROJECT=innovize-ai bash setup-gcp.sh --dry-run      # show what would happen, change nothing
#   GCP_PROJECT=innovize-ai bash setup-gcp.sh                # run all steps
#   GCP_PROJECT=innovize-ai bash setup-gcp.sh --from iam     # resume from a step and run the rest
#   GCP_PROJECT=innovize-ai bash setup-gcp.sh --only trigger # run just that one step
#   GCP_PROJECT=innovize-ai bash setup-gcp.sh --only secrets --update
#                                                            # push changed .env values as new secret versions
#
# Steps: env | apis | artifact-registry | secrets | trigger | iam
#
# The secret names below must match the --set-secrets list in cloudbuild.yaml.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
AR_REGION="${GCP_AR_REGION:-asia-south1}"    # Artifact Registry region, as in cloudbuild.yaml
REPO="speed-to-lead"
GITHUB_OWNER="${GITHUB_OWNER:-Innovize-AI}"
GITHUB_REPO="${GITHUB_REPO:-code-sapien}"
BRANCH_PATTERN="${BRANCH_PATTERN:-^speed-to-lead$}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

# ── Arguments ──────────────────────────────────────────────────────────────────
STEPS=(env apis artifact-registry secrets trigger iam)
FROM_STEP="${FROM_STEP:-}"
ONLY_STEP=""
UPDATE=false
DRY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=true; shift ;;
    --from)    FROM_STEP="${2:-}"; shift 2 ;;
    --only)    ONLY_STEP="${2:-}"; shift 2 ;;
    --update)  UPDATE=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -n "$FROM_STEP" ]]; then
  ok=false; for s in "${STEPS[@]}"; do [[ "$s" == "$FROM_STEP" ]] && ok=true; done
  $ok || { echo "ERROR: unknown step '$FROM_STEP'. Steps: ${STEPS[*]}"; exit 1; }
fi

if [[ -n "$ONLY_STEP" ]]; then
  ok=false; for s in "${STEPS[@]}"; do [[ "$s" == "$ONLY_STEP" ]] && ok=true; done
  $ok || { echo "ERROR: unknown step '$ONLY_STEP'. Steps: ${STEPS[*]}"; exit 1; }
  [[ -n "$FROM_STEP" ]] && { echo "ERROR: use --only or --from, not both"; exit 1; }
fi

_skip=false
[[ -n "$FROM_STEP" ]] && _skip=true

should_run() {
  local step=$1
  if [[ -n "$ONLY_STEP" ]]; then
    if [[ "$step" == "$ONLY_STEP" ]]; then return 0; fi
    echo "⏭  Skipping: $step"
    return 1
  fi
  if $_skip; then
    if [[ "$step" == "$FROM_STEP" ]]; then
      _skip=false
    else
      echo "⏭  Skipping: $step"
      return 1
    fi
  fi
  return 0
}

# gcloud wrapper: in a dry run it prints the command instead of running it
gc() {
  if $DRY; then echo "  [dry-run] gcloud $*"; else gcloud "$@"; fi
}
# true when the thing exists. A dry run assumes nothing exists, so every create is shown.
exists() { if $DRY; then return 1; else "$@" &>/dev/null; fi; }

echo "Project : $PROJECT_ID"
echo "Region  : $AR_REGION (Artifact Registry)"
$DRY && echo "Mode    : DRY RUN, nothing will be created or changed"
[[ -n "$FROM_STEP" ]] && echo "Resuming from: $FROM_STEP"
[[ -n "$ONLY_STEP" ]] && echo "Running only: $ONLY_STEP"
echo ""

# ── Step: env ──────────────────────────────────────────────────────────────────
# Always load, even when resuming, because later steps use the values.
load_env() {
  local file=$1
  if [[ ! -f "$file" ]]; then
    echo "  (not found: $file)"
    return
  fi
  echo "  Loading $file"
  while IFS= read -r line; do
    line="${line//$'\r'/}"
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key// /}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ "$value" =~ ^\"(.*)\"$ ]]; then value="${BASH_REMATCH[1]}"; fi
    if [[ "$value" =~ ^\'(.*)\'$ ]]; then value="${BASH_REMATCH[1]}"; fi
    export "$key=$value"
  done < "$file"
}
echo "▶ [env] Loading .env..."
load_env "$SCRIPT_DIR/backend/.env"

# ── Step: apis ─────────────────────────────────────────────────────────────────
if should_run "apis"; then
  echo "▶ [apis] Enabling GCP APIs..."
  gc services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    --project="$PROJECT_ID" --quiet
  echo "  ✓ APIs enabled"
fi

# ── Step: artifact-registry ────────────────────────────────────────────────────
if should_run "artifact-registry"; then
  echo "▶ [artifact-registry] Creating Artifact Registry repo '$REPO'..."
  if exists gcloud artifacts repositories describe "$REPO" --location="$AR_REGION" --project="$PROJECT_ID"; then
    echo "  ✓ Already exists (skipping)"
  else
    gc artifacts repositories create "$REPO" \
      --repository-format=docker \
      --location="$AR_REGION" \
      --project="$PROJECT_ID" --quiet
    echo "  ✓ Created: $REPO"
  fi
fi

# ── Step: secrets ──────────────────────────────────────────────────────────────
if should_run "secrets"; then
  # push_secret <secret name> <env var> <description> [required|optional|generate]
  #   required : must have a value (asks if missing)
  #   optional : an empty value becomes a placeholder "-" so Cloud Run can still mount it
  #   generate : an empty value becomes a random token, shown once so it can be pasted into Meta
  push_secret() {
    local name=$1 env_var=$2 prompt=$3 mode=${4:-required}
    local value="${!env_var:-}"

    if exists gcloud secrets describe "$name" --project="$PROJECT_ID"; then
      # Nothing to push when .env has no value for it
      if [[ -z "$value" ]]; then
        echo "  ✓ $name already exists (skipping)"
        return 0
      fi
      # Compare without ever printing a value
      local current
      current="$(gcloud secrets versions access latest --secret="$name" --project="$PROJECT_ID" 2>/dev/null || true)"
      if [[ "$current" == "-" ]]; then
        # an optional secret created earlier with a placeholder: replace it now that .env has a real value
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID" --quiet >/dev/null
        echo "  ✓ $name was a placeholder, now set from \$$env_var"
      elif $UPDATE && [[ "$current" != "$value" ]]; then
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID" --quiet >/dev/null
        echo "  ✓ $name updated from \$$env_var (new version)"
      elif $UPDATE; then
        echo "  ✓ $name already matches \$$env_var (no change)"
      else
        echo "  ✓ $name already exists (skipping). Use --update to push a changed value."
      fi
      return 0
    fi

    if $DRY; then
      if [[ -n "$value" ]]; then echo "  [dry-run] would create $name from \$$env_var (value is set)"
      elif [[ "$mode" == "generate" ]]; then echo "  [dry-run] would create $name with a generated random token"
      elif [[ "$mode" == "optional" ]]; then echo "  [dry-run] would create $name with a placeholder (\$$env_var is empty)"
      else echo "  [dry-run] would ASK for $prompt (\$$env_var is empty)"; fi
      return 0
    fi

    if [[ -z "$value" ]]; then
      if [[ "$mode" == "generate" ]]; then
        value="$(openssl rand -hex 24)"
        echo "  $env_var is empty. Generated a token for $name:"
        echo "    $value"
        echo "    Use this exact value as the Verify token when you register the webhook in Meta."
        echo "    Also add META_WEBHOOK_VERIFY_TOKEN=$value to backend/.env."
      else
        echo -n "  $env_var not set. Enter $prompt"
        [[ "$mode" == "optional" ]] && echo -n " (leave empty to skip)"
        echo -n ": "
        read -rs value; echo
      fi
    else
      echo "  Using \$$env_var → $name"
    fi

    if [[ -z "$value" ]]; then
      if [[ "$mode" == "optional" ]]; then
        echo -n "-" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID" --quiet
        echo "  (created $name with a placeholder, update it later)"
        return 0
      fi
      echo "  ERROR: no value for $name"
      return 1
    fi

    echo -n "$value" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID" --quiet
    echo "  ✓ Created $name"
  }

  echo "▶ [secrets] Creating secrets..."
  push_secret "stl-database-url"             "DATABASE_URL"               "PostgreSQL URL"
  push_secret "stl-google-api-key"           "GOOGLE_API_KEY"             "Google API key (Gemini)"
  push_secret "stl-pinecone-api-key"         "PINECONE_API_KEY"           "Pinecone API key"
  push_secret "stl-supabase-anon-key"        "SUPABASE_ANON_KEY"          "Supabase anon key"
  push_secret "stl-supabase-service-role-key" "SUPABASE_SERVICE_ROLE_KEY" "Supabase service-role key"
  push_secret "stl-meta-webhook-verify-token" "META_WEBHOOK_VERIFY_TOKEN" "Meta webhook verify token" generate
  push_secret "stl-meta-app-secret"          "META_APP_SECRET"            "Meta app secret"            optional
  push_secret "stl-meta-access-token"        "META_ACCESS_TOKEN"          "Meta access token"          optional
  push_secret "stl-gmail-user"               "GMAIL_USER"                 "Gmail sender address"       optional
  push_secret "stl-gmail-password"           "GMAIL_PASSWORD"             "Gmail app password"         optional
  push_secret "stl-langchain-api-key"        "LANGCHAIN_API_KEY"          "LangSmith API key"          optional
  echo "  Note: META_APP_SECRET is needed before production will accept any webhook request."
  if $UPDATE && ! $DRY; then
    echo ""
    echo "  Cloud Run reads a secret when a revision starts. To use the new versions now, start a new revision:"
    echo "    gcloud run services update speed-to-lead-backend --region us-central1 --update-labels redeploy=\$(date +%s)"
  fi
fi

# ── Step: trigger ──────────────────────────────────────────────────────────────
if should_run "trigger"; then
  TRIGGER_NAME="speed-to-lead-deploy-trigger"
  echo "▶ [trigger] Creating Cloud Build trigger..."
  # The build file refuses to run without these (see its preflight step)
  SUBS="_SUPABASE_URL=${SUPABASE_URL:-},_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-},_ENVIRONMENT=${ENVIRONMENT:-staging},_TEST_FORWARD_NUMBER=${TEST_FORWARD_NUMBER:-},_META_WEBHOOK_URL=${META_WEBHOOK_URL:-}"
  if exists gcloud builds triggers describe "$TRIGGER_NAME" --project="$PROJECT_ID"; then
    echo "  ✓ Trigger '$TRIGGER_NAME' already exists (skipping)"
  elif [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]] && ! $DRY; then
    echo "  ⚠ SUPABASE_URL or SUPABASE_ANON_KEY is empty in backend/.env, so the trigger would fail its preflight."
    echo "    Fill them in and run:  bash setup-gcp.sh --only trigger"
  else
    # The GitHub repository must already be connected to Cloud Build (Cloud Build, Triggers, Connect repository).
    if ! gc builds triggers create github \
        --project="$PROJECT_ID" \
        --name="$TRIGGER_NAME" \
        --repo-owner="$GITHUB_OWNER" \
        --repo-name="$GITHUB_REPO" \
        --branch-pattern="$BRANCH_PATTERN" \
        --build-config="agents/speed-to-lead/cloudbuild.yaml" \
        --included-files="agents/speed-to-lead/**" \
        --substitutions="$SUBS" \
        --description="Deploy Speed to Lead on changes under agents/speed-to-lead/" \
        --quiet; then
      echo "  ⚠ Could not create the trigger. Connect the GitHub repo $GITHUB_OWNER/$GITHUB_REPO to Cloud Build"
      echo "    first, then run:  bash setup-gcp.sh --only trigger"
    else
      echo "  ✓ Trigger created: $TRIGGER_NAME (branch pattern $BRANCH_PATTERN)"
    fi
  fi
fi

# ── Step: iam ──────────────────────────────────────────────────────────────────
if should_run "iam"; then
  echo "▶ [iam] Granting IAM permissions..."
  if $DRY; then
    PROJECT_NUMBER="PROJECT_NUMBER"
  else
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
  fi
  CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
  CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

  for role in roles/run.admin roles/iam.serviceAccountUser roles/secretmanager.secretAccessor; do
    gc projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$CB_SA" --role="$role" --condition=None --quiet
    echo "  ✓ $role → Cloud Build SA"
  done

  # Cloud Run runs as the default compute account and reads the secrets at start
  gc projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CR_SA" --role="roles/secretmanager.secretAccessor" --condition=None --quiet
  echo "  ✓ roles/secretmanager.secretAccessor → Cloud Run SA"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
$DRY && echo "  DRY RUN finished. Nothing was changed."
echo "  Setup complete."
echo ""
echo "  First deploy (manual), from the repo root:"
echo "  gcloud builds submit \\"
echo "    --config=agents/speed-to-lead/cloudbuild.yaml \\"
echo "    --substitutions=_SUPABASE_URL=...,_SUPABASE_ANON_KEY=...,_TEST_FORWARD_NUMBER=... \\"
echo "    --project=$PROJECT_ID ."
echo ""
echo "  Then register the callback URL printed by the build in Meta,"
echo "  with the verify token stored in the stl-meta-webhook-verify-token secret."
echo "═══════════════════════════════════════════════════════"
