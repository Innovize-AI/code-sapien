#!/usr/bin/env bash
# Map demo subdomains to Cloud Run services.
# Run once per new service (or after editing domains.yaml).
# Cloud Run provisions SSL automatically — just add the DNS records it prints.
#
# Usage: GCP_PROJECT=my-project ./setup-domains.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

BASE_DOMAIN=$(python3 -c "import yaml; d=yaml.safe_load(open('$SCRIPT_DIR/domains.yaml')); print(d['base_domain'])")

echo "Project : $PROJECT_ID"
echo "Base    : $BASE_DOMAIN"
echo ""

map_service() {
  local subdomain=$1 service=$2
  local domain="${subdomain}.${BASE_DOMAIN}"

  echo "▶ Mapping ${domain} → ${service}..."

  if gcloud beta run domain-mappings describe "$domain" \
       --platform=managed --project="$PROJECT_ID" &>/dev/null; then
    echo "  ✓ Already mapped — skipping (cert stays active)"
  else
    gcloud beta run domain-mappings create \
      --service="$service" \
      --domain="$domain" \
      --platform=managed \
      --project="$PROJECT_ID" \
      --quiet
    echo "  ✓ Created domain mapping for $domain"
  fi
}

# Read services from domains.yaml and call map_service
while IFS= read -r line; do
  [[ "$line" == __MAP__* ]] || continue
  parts=($line)
  map_service "${parts[1]}" "${parts[2]}"
done < <(python3 - <<EOF
import yaml
cfg = yaml.safe_load(open("$SCRIPT_DIR/domains.yaml"))
for svc in cfg.get("services", []):
    print(f"__MAP__ {svc['subdomain']} {svc['frontend_service']}")
EOF
)

# ── Print DNS records ───────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Add these CNAME records at your DNS provider:"
echo "  Record type: CNAME  |  TTL: 3600"
echo ""

python3 - <<EOF
import yaml, subprocess
cfg = yaml.safe_load(open("$SCRIPT_DIR/domains.yaml"))
base = cfg["base_domain"]

for svc in cfg.get("services", []):
    sub    = svc["subdomain"]
    domain = f"{sub}.{base}"
    try:
        result = subprocess.run([
            "gcloud", "beta", "run", "domain-mappings", "describe", domain,
            "--platform=managed",
            "--format=value(status.resourceRecords[0].rrdata)"
        ], capture_output=True, text=True)
        target = result.stdout.strip()
        if target:
            print(f"  {domain}  →  {target}")
        else:
            print(f"  {domain}  →  (run again after mapping is ready)")
    except Exception:
        pass
EOF

echo ""
echo "  After adding records, SSL provisions automatically (~15 min)."
echo "═══════════════════════════════════════════════════════════"
