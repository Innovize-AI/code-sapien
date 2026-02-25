---
description: Technical SOP for Sales Research Deployment (Google Cloud Deploy + Secrets)
---

# Sales Research Technical Deployment SOP 🏗️

This is the definitive guide for managing the Sales Research infrastructure on Google Cloud. It covers architecture, secret management, CI/CD, and troubleshooting.

## 1. Architectural Overview 🗺️
- **Project ID**: `innovize-ai`
- **Region**: `us-central1`
- **Registry**: Artifact Registry (`sales-research` repository)
- **Compute**: Cloud Run (Gen 2, CPU only allocated during requests)
- **Orchestration**: Google Cloud Deploy (Delivery Pipelines)
- **CI/CD Build Engine**: Cloud Build + Skaffold (v4beta8)

---

## 2. Managing Secrets & Config 🔐
We use a **Zero-Leak Policy**. No secrets are committed to Git or stored as literal values in YAML.

### Ingestion Flow
1. **Local `.env`**: Update your root `.env` file.
2. **Setup Script**: Run [setup_secrets.sh](file:///home/pavan/Innovize%20AI/code-sapien/sales-research/backend/scripts/setup_secrets.sh).
   - This script parses your `.env` and creates/updates versions in **Google Secret Manager**.
3. **Manifest Reference**: Use `secretKeyRef` in your deployment YAMLs.

### Required IAM for Secrets
The Cloud Run service account MUST have the `Secret Manager Secret Accessor` role. 
Check this with:
```bash
gcloud projects get-iam-policy innovize-ai \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:512561667165-compute@developer.gserviceaccount.com"
```

---

## 3. Deploying Code Updates 💻
The pipeline is fully automated via the `sales-research-cloud-deploy` branch.

### Automated Trigger
```bash
git add .
git commit -m "feat: your change"
git push origin sales-research-cloud-deploy
```

### Manual Trigger (Emergency)
If the GitHub trigger fails, you can trigger a build manually:
```bash
# From the root directory
gcloud builds submit --config sales-research/backend/cloudbuild.yaml .
```

---

## 4. Environment Parameters 🌍
Config is managed via `env` blocks in the [deploy/](file:///home/pavan/Innovize%20AI/code-sapien/sales-research/backend/deploy/) manifests.

| Variable | Key Purpose |
| :-- | :-- |
| `DB_SCHEMA` | Drives search_path (Staging uses `staging`, Prod uses `public`). |
| `ENVIRONMENT` | Used for logging and Sentry tagging. |
| `API_URL` | (Frontend only) Injected at runtime to find the correct backend. |

---

## 5. Promotion Logic 🏆
1. **Stage 1: Staging**: Every build automatically deploys to the `staging` target.
2. **Stage 2: Production**: 
   - Promotion is **manual**.
   - Go to [Cloud Deploy Console](https://console.cloud.google.com/deploy/delivery-pipelines/us-central1/glial-sales-backend-pipeline).
   - Click **Promote** on the verified release.

---

## 6. Deep-Dive Troubleshooting 🛠️

### "Permission Denied on Secret"
- **Cause**: The Service Account was changed or the IAM binding drifted.
- **Fix**: Run the IAM binding command again (found in [task.md](file:///home/pavan/.gemini/antigravity/brain/bdaf51d8-a6a7-4e24-8128-4aa172e128a3/task.md)).

### "Image Not Found"
- **Cause**: Skaffold profile name mismatch or repo cleaning.
- **Fix**: Verify `skaffold.yaml` image names match the `cloudbuild.yaml` `--default-repo` flag.

### Application 500 Errors
- **Cause**: Database search_path issues.
- **Fix**: Check Cloud Run logs for the "DB DIAGNOSTIC" block at startup. It will show the active schema and search_path.

---

## 7. Useful Admin Commands ⚡
```bash
# View active backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=glial-research-backend-service" --limit 10

# List all secrets in the project
gcloud secrets list
```
