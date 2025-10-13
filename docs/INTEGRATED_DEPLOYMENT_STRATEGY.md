# 🎯 CapitolScope Integrated Deployment Strategy

## 🔍 **Overview**

I've integrated the Cloud Run scheduler system into your existing deployment pipeline. Here's how everything works together:

## 🏗️ **Architecture Options**

### **Option 1: Cloud Run Only (Recommended)**
```
Cloud Scheduler → Worker Service → Redis → Database
     ↓               ↓            ↓         ↓
Periodic Tasks → HTTP Endpoints → Queue → Notifications
```

### **Option 2: Traditional Celery (Local/VM)**
```
Cron → Celery Beat → Redis → Celery Workers → Database
  ↓        ↓          ↓          ↓             ↓
Tasks → Scheduler → Queue → Processing → Notifications
```

## 📋 **Updated File Structure**

### **Deployment Scripts**
```
scripts/gcloud/
├── deploy_and_update.sh          # 🆕 Updated with worker deployment
├── deploy_api_cloud_run.sh       # ✅ Existing API deployment
├── deploy_frontend_cloud_run.sh  # ✅ Existing frontend deployment
├── deploy_worker_cloud_run.sh    # 🆕 New worker deployment
├── update_cloud_run_env.sh       # ✅ Existing API env vars
├── update_worker_env.sh          # 🆕 New worker env vars
└── setup_cloud_scheduler.sh      # 🆕 New scheduler setup
```

### **Docker Configuration**
```
├── Dockerfile.worker              # 🆕 Cloud Run worker
├── Dockerfile.combined            # ✅ Existing combined build
├── app/Dockerfile                 # ✅ Existing API build
└── docker-compose.yml             # 🆕 Updated with profiles
```

### **Local Testing Scripts**
```
scripts/local/
├── test-celery.sh                 # 🆕 Test traditional Celery
└── test-cloud-run.sh              # 🆕 Test Cloud Run worker
```

## 🚀 **Deployment Workflows**

### **Cloud Run Production Deployment**
```bash
# Deploy everything to Cloud Run (recommended)
./scripts/gcloud/deploy_and_update.sh
```

This now includes:
1. ✅ API service deployment
2. ✅ API environment variables
3. 🆕 **Worker service deployment**
4. 🆕 **Worker environment variables** 
5. 🆕 **Cloud Scheduler setup**
6. ✅ Frontend deployment

### **Individual Service Deployment**
```bash
# Deploy just the worker service
./scripts/gcloud/deploy_worker_cloud_run.sh
./scripts/gcloud/update_worker_env.sh

# Set up scheduler jobs
./scripts/gcloud/setup_cloud_scheduler.sh
```

## 🧪 **Local Testing Options**

### **Test Cloud Run Worker Locally**
```bash
# Test the Cloud Run worker implementation
./scripts/local/test-cloud-run.sh

# Available at:
# - API: http://localhost:8001
# - Worker: http://localhost:8082  
# - Frontend: http://localhost:5173
```

### **Test Traditional Celery Locally**
```bash
# Test traditional Celery implementation
./scripts/local/test-celery.sh

# Available at:
# - API: http://localhost:8001
# - Frontend: http://localhost:5173
# - Celery Flower: http://localhost:5555 (if enabled)
```

### **Standard Development**
```bash
# Regular development without background tasks
docker-compose -p capitolscope-dev up --build

# Only API, Redis, and Frontend
```

## 🔧 **Docker Compose Profiles**

I've added **profiles** to your `docker-compose.yml`:

### **Default Profile (No Background Tasks)**
```bash
docker-compose up
# Starts: API, Redis, Frontend only
```

### **Traditional Celery Profile**
```bash
docker-compose --profile celery up
# Starts: API, Redis, Frontend, Celery Worker, Celery Beat
```

### **Cloud Run Testing Profile**
```bash
docker-compose --profile cloud-run up  
# Starts: API, Redis, Frontend, Cloud Run Worker
```

## 🎯 **Integration Benefits**

### **Seamless Migration**
- ✅ **Same codebase** - all existing task functions work unchanged
- ✅ **Same environment variables** - no config changes needed
- ✅ **Same Redis instance** - existing Supabase Redis works
- ✅ **Same database** - existing Supabase database works

### **Flexible Testing**
- 🧪 **Local Cloud Run simulation** with Docker
- 🧪 **Traditional Celery testing** for comparison  
- 🧪 **No background tasks** for frontend-only development

### **Production Ready**
- 🚀 **One-command deployment** with `deploy_and_update.sh`
- 🚀 **Automatic scaling** with Cloud Run
- 🚀 **Cost optimization** with pay-per-use pricing
- 🚀 **Built-in monitoring** with Google Cloud

## 📊 **Service Architecture**

### **Cloud Run Services**
| Service | Purpose | URL Pattern |
|---------|---------|-------------|
| `capitolscope-api` | Main application | `capitolscope-api-*.us-west1.run.app` |
| `capitolscope-worker` | Background tasks | `capitolscope-worker-*.us-west1.run.app` |
| `capitolscope-frontend` | User interface | `capitolscope-frontend-*.us-west1.run.app` |

### **Cloud Scheduler Jobs**
| Job | Schedule | Endpoint |
|-----|----------|----------|
| congressional-data-sync | Every 2h (business) | `/scheduled/congressional-sync` |
| stock-price-updates | Every 15m (market) | `/scheduled/stock-prices` |
| notification-processing | Every 30m | `/scheduled/notifications` |
| health-checks | Every 10m | `/scheduled/health-check` |
| daily-maintenance | Daily 2 AM UTC | `/tasks/execute` |

## 🔄 **Development Workflow**

### **1. Local Development & Testing**
```bash
# Test Cloud Run approach locally
./scripts/local/test-cloud-run.sh

# Test traditional Celery approach locally  
./scripts/local/test-celery.sh

# Regular development (no background tasks)
docker-compose up
```

### **2. Deploy to Cloud Run**
```bash
# Full deployment (recommended)
./scripts/gcloud/deploy_and_update.sh

# Check deployment
curl $(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)')/health
```

### **3. Monitor & Manage**
```bash
# View scheduler jobs
gcloud scheduler jobs list --location=us-west1

# Trigger job manually
gcloud scheduler jobs run health-checks --location=us-west1

# View logs
gcloud run logs read --service=capitolscope-worker --region=us-west1
```

## 🎉 **Key Integration Points**

### **Updated Deployment Pipeline**
Your existing `deploy_and_update.sh` now:
1. ✅ Deploys API (existing)
2. ✅ Updates API environment (existing)
3. 🆕 **Deploys worker service**
4. 🆕 **Updates worker environment**
5. 🆕 **Sets up Cloud Scheduler**
6. ✅ Deploys frontend (existing)

### **Docker Compose Enhancement**
Your `docker-compose.yml` now supports:
- ✅ **Default**: API + Redis + Frontend
- 🆕 **Celery profile**: + Traditional workers
- 🆕 **Cloud Run profile**: + Cloud Run worker

### **Environment Variables**
The worker service uses the **same environment variables** as your API:
- ✅ Supabase database connection
- ✅ Redis connection (for task queuing)
- ✅ API keys (Alpha Vantage, Polygon, etc.)
- ✅ Email configuration
- ✅ All existing settings

## 🚀 **Next Steps**

### **For Cloud Run Deployment:**
```bash
# 1. Deploy everything
./scripts/gcloud/deploy_and_update.sh

# 2. Verify deployment
curl $(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)')/health/detailed

# 3. Test task execution
curl -X POST $(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)')/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"task_name": "health_check_congress_api"}'
```

### **For Local Testing:**
```bash
# Test Cloud Run approach
./scripts/local/test-cloud-run.sh

# Test endpoints
curl http://localhost:8082/health
curl http://localhost:8082/admin/queue-status
```

The integration is complete and ready for deployment! Your scheduler system is now part of your standard Cloud Run deployment pipeline. 🎯



