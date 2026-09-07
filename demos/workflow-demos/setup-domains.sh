#!/usr/bin/env bash
# Map demo subdomains to Cloud Run services.
# Run once per new service (or after editing domains.yaml).
# Cloud Run provisions SSL automatically — just add the DNS records it prints.
#
# Usage: GCP_PROJECT=my-project ./setup-domains.sh

set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-asia-south1}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

# Parse domains.yaml (requires python3, which is always available)
BASE_DOMAIN=$(python3 -c "import yaml,sys; d=yaml.safe_load(open('domains.yaml')); print(d['base_domain'])")

echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo "Base    : $BASE_DOMAIN"
echo ""

DNS_RECORDS=()

map_service() {
  local subdomain=$1 service=$2
  local domain="${subdomain}.${BASE_DOMAIN}"

  echo "▶ Mapping ${domain} → ${service}..."

  # Create or update domain mapping
  if gcloud run domain-mappings describe "$domain" \
       --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ Already mapped — skipping (cert stays active)"
  else
    gcloud run domain-mappings create \
      --service="$service" \
      --domain="$domain" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --quiet

    # Capture the DNS record Cloud Run needs
    RECORD=$(gcloud run domain-mappings describe "$domain" \
      --region="$REGION" --project="$PROJECT_ID" \
      --format="value(status.resourceRecords[0].rrdata)")
    DNS_RECORDS+=("CNAME  ${subdomain}.demos  →  ${RECORD}")
    echo "  ✓ Created — add DNS record below"
  fi
}

# Read services from domains.yaml and apply mappings
python3 - <<'EOF'
import yaml, subprocess, sys

cfg = yaml.safe_load(open("domains.yaml"))
region = cfg["region"]
services = cfg.get("services", [])

for svc in services:
    subdomain = svc["subdomain"]
    frontend  = svc["frontend_service"]
    backend   = svc.get("backend_service")
    print(f"__MAP__ {subdomain} {frontend}")
    if backend:
        print(f"__MAP__ {subdomain}-api {backend}")
EOF

# Re-read and actually call map_service from bash (so gcloud runs in this shell)
while IFS= read -r line; do
  [[ "$line" == __MAP__* ]] || continue
  parts=($line)
  map_service "${parts[1]}" "${parts[2]}"
done < <(python3 - <<'EOF'
import yaml
cfg = yaml.safe_load(open("domains.yaml"))
for svc in cfg.get("services", []):
    print(f"__MAP__ {svc['subdomain']} {svc['frontend_service']}")
EOF
)

# ── Print DNS instructions ──────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Add these CNAME records at your DNS provider"
echo "  (wherever innovizeai.com is managed):"
echo ""
echo "  Record type: CNAME"
echo "  TTL: 3600"
echo ""

python3 - <<'EOF'
import yaml, subprocess
cfg = yaml.safe_load(open("domains.yaml"))
region = cfg["region"]
base   = cfg["base_domain"]   # demos.innovizeai.com

for svc in cfg.get("services", []):
    sub    = svc["subdomain"]
    domain = f"{sub}.{base}"
    try:
        result = subprocess.run([
            "gcloud", "run", "domain-mappings", "describe", domain,
            f"--region={region}", "--format=value(status.resourceRecords[0].rrdata)"
        ], capture_output=True, text=True)
        target = result.stdout.strip()
        if target:
            print(f"  {sub}.demos.innovizeai.com  →  {target}")
        else:
            print(f"  {sub}.demos.innovizeai.com  →  (run again after deploy completes)")
    except Exception:
        pass
EOF

echo ""
echo "  After adding records, SSL certificates provision automatically"
echo "  (usually within 15 minutes)."
echo "═══════════════════════════════════════════════════════════"
