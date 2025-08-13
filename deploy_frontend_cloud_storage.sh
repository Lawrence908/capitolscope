#!/bin/bash
set -euo pipefail

export PROJECT_ID=capitolscope
export BUCKET_NAME=capitolscope-frontend-capitolscope
export API_URL=https://capitolscope-api-k23f5lpvca-uw.a.run.app

echo "Deploying frontend to Cloud Storage..."

# Navigate to frontend directory
cd frontend

# Clean previous build
echo "Cleaning previous build..."
rm -rf dist/

# Fix permission issues with .vite cache
echo "Fixing permission issues..."
if [ -d "node_modules/.vite" ]; then
    echo "Removing problematic .vite cache..."
    sudo rm -rf node_modules/.vite 2>/dev/null || rm -rf node_modules/.vite 2>/dev/null || true
fi

# Install dependencies if needed
echo "Installing dependencies..."
npm ci

# Build with API URL
echo "Building with API URL: $API_URL"
VITE_API_URL=$API_URL npm run build

# Verify build output
if [ ! -d "dist" ]; then
    echo "Error: Build failed - dist directory not found"
    exit 1
fi

echo "Build successful! Deploying to Cloud Storage..."

# Deploy to existing bucket
gcloud storage cp -r dist/* gs://$BUCKET_NAME/

# Note: Bucket has uniform bucket-level access enabled
# Files are already publicly readable if bucket is configured for public access
echo "Files uploaded successfully!"
echo "Note: Bucket has uniform bucket-level access enabled."
echo "If files are not publicly accessible, configure bucket-level IAM permissions:"
echo "gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \\"
echo "  --member=allUsers --role=roles/storage.objectViewer"

echo "Frontend deployed to Cloud Storage!"
echo "URL: https://storage.googleapis.com/$BUCKET_NAME/index.html"
echo "Or your custom domain if configured."
