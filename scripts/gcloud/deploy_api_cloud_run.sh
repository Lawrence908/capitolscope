cd /home/chris/github/CapitolScope
set -euo pipefail

# Required config
export PROJECT_ID=capitolscope
export REGION=us-west1

# Note: Environment variables are managed separately via update_cloud_run_env.sh
# This script only handles building, pushing, and deploying the container
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# Create repo once (idempotent)
gcloud artifacts repositories create capitolscope --repository-format=docker --location=$REGION --description="CapitolScope images" || true

# Build and push
IMG=us-west1-docker.pkg.dev/$PROJECT_ID/capitolscope/capitolscope-api:$(date +%Y%m%d-%H%M%S)
docker build -f app/Dockerfile -t $IMG .
docker push $IMG

# Deploy (environment variables are managed separately)
gcloud run deploy capitolscope-api \
  --image $IMG --region $REGION --allow-unauthenticated \
  --cpu=1 --memory=512Mi --min-instances=0

echo ""
echo "✅ Deployment completed successfully!"
echo "📝 Note: To update environment variables, run: ./scripts/gcloud/update_cloud_run_env.sh"