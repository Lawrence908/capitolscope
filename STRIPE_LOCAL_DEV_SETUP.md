# Stripe Local Development Setup

## Overview
This guide explains how to test Stripe webhooks locally while your production webhook points to your Cloud Run backend.

## Current Setup

### Production (Cloud Run)
- **Webhook URL**: `https://capitolscope-api-1074255918859.us-west1.run.app/api/v1/stripe/webhook`
- **Success URL**: `https://capitolscope.chrislawrence.ca/dashboard?payment=success`
- **Cancel URL**: `https://capitolscope.chrislawrence.ca/premium?payment=cancelled`

### Local Development
- **Webhook URL**: `localhost:8000/api/v1/stripe/webhook` (forwarded via Stripe CLI)
- **Success URL**: `http://localhost:3000/dashboard?payment=success`
- **Cancel URL**: `http://localhost:3000/premium?payment=cancelled`

## Local Development Workflow

### 1. Start Local Development
```bash
# Start your local Docker containers
capitol-build

# In a separate terminal, start Stripe webhook forwarding
capitol-stripe-webhook
```

### 2. What the Stripe CLI Does
The `capitol-stripe-webhook` command:
- Listens for webhook events from your Stripe sandbox
- Forwards them to `localhost:8000/api/v1/stripe/webhook`
- Provides a webhook signing secret for local testing
- Shows real-time webhook events in the terminal

### 3. Environment Variables for Local Dev
Make sure your local `.env` file has:
```bash
# Local development URLs
STRIPE_SUCCESS_URL=http://localhost:3000/dashboard?payment=success
STRIPE_CANCEL_URL=http://localhost:3000/premium?payment=cancelled
STRIPE_WEBHOOK_ENDPOINT=http://localhost:8000/api/v1/stripe/webhook
```

## Switching Between Local and Production

### For Local Testing
1. Start local containers: `capitol-build`
2. Start webhook forwarding: `capitol-stripe-webhook`
3. Use local URLs in your frontend

### For Production Testing
1. Deploy to Cloud Run: `capitol-deploy-backend`
2. Update environment variables: `capitol-update-env`
3. Use production URLs in your frontend

## Stripe Dashboard Configuration

### Current Setup (Production)
- **Webhook Endpoint**: `https://capitolscope-api-1074255918859.us-west1.run.app/api/v1/stripe/webhook`
- **Events**: All subscription and payment events

### For Local Testing
- **Webhook Endpoint**: `http://localhost:8000/api/v1/stripe/webhook` (via Stripe CLI)
- **Events**: Same events, but forwarded locally

## Commands Reference

```bash
# Local development
capitol-build                    # Start local containers
capitol-stripe-webhook          # Forward Stripe webhooks locally
capitol-logs                    # View container logs

# Production deployment
capitol-deploy-backend          # Deploy backend to Cloud Run
capitol-update-env              # Update environment variables
capitol-deploy-frontend         # Deploy frontend to Cloud Run
```

## Troubleshooting

### Webhook Not Receiving Events
1. Check if Stripe CLI is running: `capitol-stripe-webhook`
2. Verify local containers are running: `capitol-logs`
3. Check webhook endpoint is accessible: `curl http://localhost:8000/api/v1/stripe/webhook`

### Production Webhook Errors
1. Check Cloud Run logs in Google Cloud Console
2. Verify environment variables are set: `capitol-update-env`
3. Test webhook endpoint: `curl https://capitolscope-api-1074255918859.us-west1.run.app/api/v1/stripe/webhook`

## Migration to Production

When you're ready to go live:
1. Update Stripe dashboard webhook URL to production
2. Update environment variables to production URLs
3. Deploy both frontend and backend
4. Test with real payments (small amounts first)

## Notes
- Stripe CLI automatically handles webhook signing for local development
- You don't need to change the webhook URL in Stripe dashboard for local testing
- The CLI creates a temporary webhook endpoint that forwards to your local server
- All webhook events are logged in the CLI terminal for debugging
