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
)

# Function to create or update a secret
create_secret() {
  local secret_name=$1
  local secret_value=$2

  if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
    echo "Secret $secret_name already exists. Updating version..."
  else
    echo "Creating secret $secret_name..."
    gcloud secrets create "$secret_name" --replication-policy="automatic"
  fi

  echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
}

# Function to get value from .env, handling spaces around = and quotes
get_env_val() {
  local key=$1
  local file="../../../.env"
  if [ -f "$file" ]; then
    # Search for key=val, key = val, etc. and extract the value part
    local line=$(grep -E "^${key}[[:space:]]*=" "$file" | head -n 1)
    if [ -n "$line" ]; then
      # Extract everything after the first = and trim whitespace and outer quotes
      local val=$(echo "$line" | cut -d'=' -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
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
