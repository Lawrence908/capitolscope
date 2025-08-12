#!/bin/bash
set -euo pipefail

export PROJECT_ID=capitolscope
export REGION=us-west1
export API_URL=https://capitolscope-api-k23f5lpvca-uw.a.run.app

echo "Deploying frontend to Cloud Run..."

# Build and push frontend
cd frontend
IMG=us-west1-docker.pkg.dev/$PROJECT_ID/capitolscope/capitolscope-frontend:$(date +%Y%m%d-%H%M%S)
docker build -f Dockerfile.prod --build-arg VITE_API_URL=$API_URL -t $IMG .
docker push $IMG

# Deploy frontend service
gcloud run deploy capitolscope-frontend \
  --image $IMG --region $REGION --allow-unauthenticated \
  --cpu=1 --memory=512Mi --min-instances=0 \
  --port=80

echo "Frontend deployed! URL:"
gcloud run services describe capitolscope-frontend --region $REGION --format='value(status.url)'

