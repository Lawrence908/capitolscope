#!/bin/bash
set -euo pipefail

# Configuration
SERVICE_NAME=capitolscope-worker
REGION=us-west1
ENV_FILE=.env

echo "🔄 Updating Cloud Run worker environment variables from .env file..."
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo ""

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found!"
    exit 1
fi

# Function to get value from .env file
get_env_value() {
    local key=$1
    local value=$(grep "^$key=" "$ENV_FILE" | cut -d'=' -f2- | xargs)
    echo "$value"
}

echo "📖 Reading environment variables from $ENV_FILE..."

# Core application settings
ENVIRONMENT=$(get_env_value "ENVIRONMENT")
DEBUG=$(get_env_value "DEBUG")
LOG_LEVEL=$(get_env_value "LOG_LEVEL")

# Database Configuration
DATABASE_PROVIDER=$(get_env_value "DATABASE_PROVIDER")
SUPABASE_URL=$(get_env_value "SUPABASE_URL")
SUPABASE_KEY=$(get_env_value "SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY=$(get_env_value "SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_JWT_SECRET=$(get_env_value "SUPABASE_JWT_SECRET")
SUPABASE_PASSWORD=$(get_env_value "SUPABASE_PASSWORD")
DATABASE_ECHO=$(get_env_value "DATABASE_ECHO")
DATABASE_POOL_SIZE=$(get_env_value "DATABASE_POOL_SIZE")
DATABASE_MAX_OVERFLOW=$(get_env_value "DATABASE_MAX_OVERFLOW")

# Redis Configuration for task queuing
REDIS_HOST=$(get_env_value "REDIS_HOST")
REDIS_USER=$(get_env_value "REDIS_USER")
REDIS_PASSWORD=$(get_env_value "REDIS_PASSWORD")
REDIS_PORT=$(get_env_value "REDIS_PORT")
REDIS_DB=$(get_env_value "REDIS_DB")
CELERY_BROKER_URL=$(get_env_value "CELERY_BROKER_URL")
CELERY_RESULT_BACKEND=$(get_env_value "CELERY_RESULT_BACKEND")

# API Keys for data sources
ALPHA_VANTAGE_API_KEY=$(get_env_value "ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL=$(get_env_value "ALPHA_VANTAGE_BASE_URL")
POLYGON_API_KEY=$(get_env_value "POLYGON_API_KEY")
OPEN_FIGI_API_KEY=$(get_env_value "OPEN_FIGI_API_KEY")
CONGRESS_GOV_API_KEY=$(get_env_value "CONGRESS_GOV_API_KEY")

# Email Configuration for notifications
EMAIL_HOST=$(get_env_value "EMAIL_HOST")
EMAIL_PORT=$(get_env_value "EMAIL_PORT")
EMAIL_USER=$(get_env_value "EMAIL_USER")
EMAIL_PASSWORD=$(get_env_value "EMAIL_PASSWORD")
EMAIL_FROM=$(get_env_value "EMAIL_FROM")
EMAIL_USE_TLS=$(get_env_value "EMAIL_USE_TLS")

# Worker-specific settings
CELERY_PRODUCTION=true
LOG_DIR=/tmp/logs

# Check if required variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$CELERY_BROKER_URL" ] || [ -z "$EMAIL_USER" ]; then
    echo "❌ Error: Required environment variables not found in $ENV_FILE"
    echo "  Required: SUPABASE_URL, CELERY_BROKER_URL, EMAIL_USER"
    exit 1
fi

echo "  ✅ Core Configuration"
echo "  ✅ Database Configuration"
echo "  ✅ Redis Configuration"
echo "  ✅ API Keys"
echo "  ✅ Email Configuration"

echo ""
echo "🚀 Updating Cloud Run worker service..."

# Update the service with environment variables
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --set-env-vars="ENVIRONMENT=$ENVIRONMENT,DEBUG=$DEBUG,LOG_LEVEL=$LOG_LEVEL,DATABASE_PROVIDER=$DATABASE_PROVIDER,SUPABASE_URL=$SUPABASE_URL,SUPABASE_KEY=$SUPABASE_KEY,SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY,SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET,SUPABASE_PASSWORD=$SUPABASE_PASSWORD,DATABASE_ECHO=$DATABASE_ECHO,DATABASE_POOL_SIZE=$DATABASE_POOL_SIZE,DATABASE_MAX_OVERFLOW=$DATABASE_MAX_OVERFLOW,REDIS_HOST=$REDIS_HOST,REDIS_USER=$REDIS_USER,REDIS_PASSWORD=$REDIS_PASSWORD,REDIS_PORT=$REDIS_PORT,REDIS_DB=$REDIS_DB,CELERY_BROKER_URL=$CELERY_BROKER_URL,CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND,ALPHA_VANTAGE_API_KEY=$ALPHA_VANTAGE_API_KEY,ALPHA_VANTAGE_BASE_URL=$ALPHA_VANTAGE_BASE_URL,POLYGON_API_KEY=$POLYGON_API_KEY,OPEN_FIGI_API_KEY=$OPEN_FIGI_API_KEY,CONGRESS_GOV_API_KEY=$CONGRESS_GOV_API_KEY,EMAIL_HOST=$EMAIL_HOST,EMAIL_PORT=$EMAIL_PORT,EMAIL_USER=$EMAIL_USER,EMAIL_PASSWORD=$EMAIL_PASSWORD,EMAIL_FROM=$EMAIL_FROM,EMAIL_USE_TLS=$EMAIL_USE_TLS,CELERY_PRODUCTION=$CELERY_PRODUCTION,LOG_DIR=$LOG_DIR"

echo ""
echo "✅ Worker environment variables updated successfully!"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format='value(status.url)')
echo "🌐 Worker Service URL: $SERVICE_URL"

echo ""
echo "🔍 Testing worker service..."
if curl -f -s "$SERVICE_URL/health/detailed" > /dev/null; then
    echo "✅ Worker health check passed"
else
    echo "❌ Worker health check failed"
    echo "🔧 Try checking the logs: gcloud run logs read --service=$SERVICE_NAME --region=$REGION"
fi

echo ""
echo "📊 Current environment variables:"
gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(spec.template.spec.containers[0].env[].name)" | tr ';' '\n' | sort



