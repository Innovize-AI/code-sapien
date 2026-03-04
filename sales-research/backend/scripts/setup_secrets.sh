#!/bin/bash

# List of secrets to create
SECRETS=(
  "OPENAI_API_KEY"
  "LANGCHAIN_API_KEY"
  "LANGCHAIN_TRACING_V2"
  "LANGCHAIN_ENDPOINT"
  "LANGCHAIN_PROJECT"
  "TAVILY_API_KEY"
  "GOOGLE_API_KEY"
  "ANTHROPIC_API_KEY"
  "GOOGLE_DRIVE_FOLDER_ID"
  "CLAUDE_API_KEY"
  "APOLLO_API_KEY"
  "RAPID_API_KEY"
  "N8N_WEBHOOK_URL"
  "SUPABASE_URL"
  "SUPABASE_ANON_KEY"
  "SUPABASE_SERVICE_ROLE_KEY"
  "DB_PASSWORD"
  "DATABASE_URL"
  "LINKEDIN_RAPID_BASE_URL"
  "PINECONE_API_KEY"
  "TASK_SECRET"
)

# Function to create or update a secret
create_secret() {
  local secret_name=$1
  local secret_value=$2

  if gcloud secrets describe "$secret_name" --quiet >/dev/null 2>&1; then
    # Fetch current latest value
    local current_value=$(gcloud secrets versions access latest --secret="$secret_name" --quiet 2>/dev/null)
    
    if [ "$current_value" == "$secret_value" ]; then
      echo "Secret $secret_name already exists and matches. Skipping update..."
      return 0
    else
      echo "Secret $secret_name exists but value is different. Updating version..."
    fi
  else
    echo "Creating secret $secret_name..."
    gcloud secrets create "$secret_name" --replication-policy="automatic" --quiet
  fi

  echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=- --quiet
}

# Function to get value from .env, handling spaces around = and quotes
get_env_val() {
  local key=$1
  # Calculate path relative to the script itself
  local script_dir=$(dirname "$(readlink -f "$0")")
  local file="$script_dir/../../../.env"
  
  if [ -f "$file" ]; then
    # Search for key=val, key = val, etc. and extract the value part
    local line=$(grep -E "^${key}[[:space:]]*=" "$file" | head -n 1)
    if [ -n "$line" ]; then
      # Extract everything after the first =
      local val=$(echo "$line" | cut -d'=' -f2-)
      # Trim leading/trailing whitespace
      val=$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
      # Strip leading/trailing double or single quotes
      val=$(echo "$val" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      echo "$val"
    fi
  fi
}

# Iterate and create secrets
for secret in "${SECRETS[@]}"; do
  val=$(get_env_val "$secret")
  
  # If not in .env, check current environment
  if [ -z "$val" ]; then
    val="${!secret}"
  fi

  if [ -n "$val" ]; then
    create_secret "$secret" "$val"
  else
    echo "Warning: $secret not found in .env or environment"
  fi
done

echo "Secret provisioning complete!"
