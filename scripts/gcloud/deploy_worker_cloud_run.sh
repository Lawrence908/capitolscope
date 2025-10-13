#!/bin/bash
set -euo pipefail

# Configuration
export PROJECT_ID=capitolscope
export REGION=us-west1
export SERVICE_NAME=capitolscope-worker

echo "🔧 Deploying CapitolScope Background Worker to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Set project and region
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Enable required APIs
echo "📋 Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo "🏗️ Creating Artifact Registry repository..."
gcloud artifacts repositories create capitolscope --repository-format=docker --location=$REGION --description="CapitolScope images" 2>/dev/null || echo "Repository already exists"

# Build and push Docker image
echo "🐳 Building and pushing Docker image..."
IMG=us-west1-docker.pkg.dev/$PROJECT_ID/capitolscope/capitolscope-worker:$(date +%Y%m%d-%H%M%S)
docker build -f Dockerfile.worker -t $IMG .
docker push $IMG

echo "✅ Image pushed: $IMG"

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMG \
  --region $REGION \
  --allow-unauthenticated \
  --cpu=2 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=900 \
  --concurrency=10 \
  --port=8080

echo ""
echo "✅ Worker service deployed successfully!"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')
echo "🌐 Service URL: $SERVICE_URL"

# Test health endpoint
echo ""
echo "🔍 Testing health endpoint..."
if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

echo ""
echo "📝 Next steps:"
echo "1. Update environment variables: ./scripts/gcloud/update_worker_env.sh"
echo "2. Set up Cloud Scheduler jobs: ./scripts/gcloud/setup_cloud_scheduler.sh"
echo "3. Test worker endpoints: curl $SERVICE_URL/health/detailed"



