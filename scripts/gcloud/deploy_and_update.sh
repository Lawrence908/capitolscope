#!/bin/bash
set -euo pipefail

echo "🚀 Starting CapitolScope full deployment and environment update..."
echo ""

# Step 1: Deploy the API application
echo "📦 Step 1: Deploying API application..."
./scripts/gcloud/deploy_api_cloud_run.sh

echo ""
echo "⏳ Waiting for API deployment to complete..."
sleep 10

# Step 2: Update API environment variables
echo "🔧 Step 2: Updating API environment variables..."
./scripts/gcloud/update_cloud_run_env.sh

echo ""
echo "⏳ Waiting for environment update to complete..."
sleep 5

# Step 3: Deploy the background worker service
echo "🔧 Step 3: Deploying background worker service..."
./scripts/gcloud/deploy_worker_cloud_run.sh

echo ""
echo "⏳ Waiting for worker deployment to complete..."
sleep 10

# Step 4: Update worker environment variables
echo "🔧 Step 4: Updating worker environment variables..."
./scripts/gcloud/update_worker_env.sh

echo ""
echo "⏳ Waiting for worker environment update to complete..."
sleep 5

# Step 5: Set up Cloud Scheduler jobs
echo "⏰ Step 5: Setting up Cloud Scheduler jobs..."
./scripts/gcloud/setup_cloud_scheduler.sh

echo ""
echo "⏳ Waiting for scheduler setup to complete..."
sleep 5

# Step 6: Deploy the frontend application
echo "🌐 Step 6: Deploying frontend application..."
./scripts/gcloud/deploy_frontend_cloud_run.sh

echo ""
echo "🎉 Full deployment and environment update completed successfully!"
echo "🌐 Your API, worker, and frontend applications should now be running with the latest code and configuration."
echo ""
echo "📋 Deployed services:"
echo "  • API Service: capitolscope-api"
echo "  • Worker Service: capitolscope-worker"
echo "  • Frontend Service: capitolscope-frontend"
echo ""
echo "⏰ Scheduled jobs:"
echo "  • Congressional data sync: Every 2 hours (business hours)"
echo "  • Stock price updates: Every 15 minutes (market hours)"
echo "  • Notification processing: Every 30 minutes"
echo "  • Health checks: Every 10 minutes"
echo "  • Daily maintenance: Daily at 2 AM UTC"
echo ""
echo "🔍 Test your worker service:"
WORKER_URL=$(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)' 2>/dev/null || echo "Worker service not found")
if [ "$WORKER_URL" != "Worker service not found" ]; then
    echo "  curl $WORKER_URL/health"
else
    echo "  ❌ Could not get worker service URL"
fi
