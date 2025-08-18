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

# Step 3: Deploy the frontend application
echo "🌐 Step 3: Deploying frontend application..."
./scripts/gcloud/deploy_frontend_cloud_run.sh

echo ""
echo "🎉 Full deployment and environment update completed successfully!"
echo "🌐 Your API and frontend applications should now be running with the latest code and configuration."
