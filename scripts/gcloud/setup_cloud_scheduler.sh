#!/bin/bash
set -euo pipefail

# Configuration
PROJECT_ID=capitolscope
REGION=us-west1
WORKER_SERVICE_NAME=capitolscope-worker

echo "⏰ Setting up Cloud Scheduler jobs for CapitolScope..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Enable Cloud Scheduler API
echo "📋 Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com

# Get worker service URL
echo "🔍 Getting worker service URL..."
WORKER_URL=$(gcloud run services describe $WORKER_SERVICE_NAME --region=$REGION --format='value(status.url)')

if [ -z "$WORKER_URL" ]; then
    echo "❌ Error: Could not get worker service URL"
    echo "💡 Make sure the worker service is deployed first:"
    echo "   ./scripts/gcloud/deploy_worker_cloud_run.sh"
    exit 1
fi

echo "✅ Worker URL: $WORKER_URL"

# Create Cloud Scheduler jobs

echo ""
echo "⏰ Creating Cloud Scheduler jobs..."

# 1. Congressional data sync - every 2 hours during business hours (8 AM - 6 PM ET)
echo "📊 Creating congressional data sync job..."
gcloud scheduler jobs create http congressional-data-sync \
    --location=$REGION \
    --schedule="0 */2 8-18 * * MON-FRI" \
    --time-zone="America/New_York" \
    --uri="$WORKER_URL/scheduled/congressional-sync" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=900s \
    --max-retry-attempts=3 \
    --max-retry-duration=3600s \
    --description="Sync congressional trading data every 2 hours during business hours" \
    || echo "Job already exists, updating..."

# If job exists, update it
gcloud scheduler jobs update http congressional-data-sync \
    --location=$REGION \
    --schedule="0 */2 8-18 * * MON-FRI" \
    --time-zone="America/New_York" \
    --uri="$WORKER_URL/scheduled/congressional-sync" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=900s \
    --max-retry-attempts=3 \
    --max-retry-duration=3600s \
    --description="Sync congressional trading data every 2 hours during business hours" \
    2>/dev/null || true

# 2. Stock price updates - every 15 minutes during market hours (9:30 AM - 4 PM ET)
echo "📈 Creating stock price update job..."
gcloud scheduler jobs create http stock-price-updates \
    --location=$REGION \
    --schedule="*/15 9-16 * * MON-FRI" \
    --time-zone="America/New_York" \
    --uri="$WORKER_URL/scheduled/stock-prices" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=300s \
    --max-retry-attempts=2 \
    --max-retry-duration=1800s \
    --description="Update stock prices every 15 minutes during market hours" \
    || echo "Job already exists, updating..."

gcloud scheduler jobs update http stock-price-updates \
    --location=$REGION \
    --schedule="*/15 9-16 * * MON-FRI" \
    --time-zone="America/New_York" \
    --uri="$WORKER_URL/scheduled/stock-prices" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=300s \
    --max-retry-attempts=2 \
    --max-retry-duration=1800s \
    --description="Update stock prices every 15 minutes during market hours" \
    2>/dev/null || true

# 3. Notification processing - every 30 minutes
echo "🔔 Creating notification processing job..."
gcloud scheduler jobs create http notification-processing \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/scheduled/notifications" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=600s \
    --max-retry-attempts=3 \
    --max-retry-duration=1800s \
    --description="Process pending notifications every 30 minutes" \
    || echo "Job already exists, updating..."

gcloud scheduler jobs update http notification-processing \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/scheduled/notifications" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=600s \
    --max-retry-attempts=3 \
    --max-retry-duration=1800s \
    --description="Process pending notifications every 30 minutes" \
    2>/dev/null || true

# 4. Health checks - every 10 minutes
echo "🏥 Creating health check job..."
gcloud scheduler jobs create http health-checks \
    --location=$REGION \
    --schedule="*/10 * * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/scheduled/health-check" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=120s \
    --max-retry-attempts=2 \
    --max-retry-duration=600s \
    --description="Perform health checks every 10 minutes" \
    || echo "Job already exists, updating..."

gcloud scheduler jobs update http health-checks \
    --location=$REGION \
    --schedule="*/10 * * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/scheduled/health-check" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --attempt-deadline=120s \
    --max-retry-attempts=2 \
    --max-retry-duration=600s \
    --description="Perform health checks every 10 minutes" \
    2>/dev/null || true

# 5. Daily maintenance - 2 AM UTC
echo "🧹 Creating daily maintenance job..."
gcloud scheduler jobs create http daily-maintenance \
    --location=$REGION \
    --schedule="0 2 * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/tasks/execute" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"task_name": "comprehensive_data_ingestion", "priority": 3}' \
    --attempt-deadline=1800s \
    --max-retry-attempts=2 \
    --max-retry-duration=3600s \
    --description="Run daily maintenance tasks at 2 AM UTC" \
    || echo "Job already exists, updating..."

gcloud scheduler jobs update http daily-maintenance \
    --location=$REGION \
    --schedule="0 2 * * *" \
    --time-zone="UTC" \
    --uri="$WORKER_URL/tasks/execute" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"task_name": "comprehensive_data_ingestion", "priority": 3}' \
    --attempt-deadline=1800s \
    --max-retry-attempts=2 \
    --max-retry-duration=3600s \
    --description="Run daily maintenance tasks at 2 AM UTC" \
    2>/dev/null || true

echo ""
echo "✅ Cloud Scheduler jobs created successfully!"
echo ""
echo "📋 Created jobs:"
echo "  • congressional-data-sync    - Every 2 hours during business hours"
echo "  • stock-price-updates        - Every 15 minutes during market hours"
echo "  • notification-processing    - Every 30 minutes"
echo "  • health-checks             - Every 10 minutes"
echo "  • daily-maintenance         - Daily at 2 AM UTC"

echo ""
echo "🔍 Verifying jobs..."
gcloud scheduler jobs list --location=$REGION --filter="name~capitolscope OR name~congressional OR name~stock OR name~notification OR name~health OR name~maintenance"

echo ""
echo "📝 Management commands:"
echo "  • List jobs:    gcloud scheduler jobs list --location=$REGION"
echo "  • Trigger job:  gcloud scheduler jobs run JOB_NAME --location=$REGION"
echo "  • Pause job:    gcloud scheduler jobs pause JOB_NAME --location=$REGION"
echo "  • Resume job:   gcloud scheduler jobs resume JOB_NAME --location=$REGION"
echo "  • Delete job:   gcloud scheduler jobs delete JOB_NAME --location=$REGION"

echo ""
echo "🧪 Testing a job..."
echo "Triggering health check job for testing..."
gcloud scheduler jobs run health-checks --location=$REGION || echo "Test trigger failed - this is normal if jobs are paused"

echo ""
echo "✅ Cloud Scheduler setup complete!"
echo "🌐 Monitor jobs at: https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
