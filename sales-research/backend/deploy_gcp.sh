#!/bin/bash

# Exit on error
set -e

# Configuration - Modify these or pass as env vars
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="glial-research-backend"
REGION="us-central1"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

echo "🚀 Starting deployment for $SERVICE_NAME to GCP Cloud Run..."

# 1. Build and Push Image
echo "📦 Building Docker image..."
docker build -t $IMAGE_TAG .

echo "📤 Pushing image to GCR..."
docker push $IMAGE_TAG

# 2. Deploy to Cloud Run
echo "クラウド Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --timeout 3600 \
  --concurrency 80 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars "ENVIRONMENT=production" \
  --cpu-throttling

# Note: We use --cpu-throttling (standard) to ensure costs stay at $0 when idle.
# The Blocking Heartbeat pattern ensures the CPU stays active during processing.

echo "✅ Backend deployed successfully!"

# 3. Create/Update Cloud Scheduler
echo "⏰ Setting up Cloud Scheduler..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

# Important: TASK_SECRET should be set in Cloud Run env vars.
# If you haven't set it yet, do so via:
# gcloud run services update $SERVICE_NAME --set-env-vars "TASK_SECRET=your_secret_here"

echo "To trigger the heartbeat every hour, run:"
echo "gcloud scheduler jobs create http $SERVICE_NAME-heartbeat \\"
echo "  --schedule=\"0 * * * *\" \\"
echo "  --uri=\"$SERVICE_URL/api/tasks/heartbeat\" \\"
echo "  --http-method=POST \\"
echo "  --headers=\"x-task-secret=YOUR_TASK_SECRET\" \\"
echo "  --location=$REGION"

echo "---"
echo "🔗 Service URL: $SERVICE_URL"
echo "⚠️  Remember to go to Google Cloud Console and set your production .env variables in the Cloud Run 'Variables & Secrets' tab."
