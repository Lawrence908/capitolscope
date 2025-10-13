# 🌐 CapitolScope Scheduler Implementation for Cloud Run

## 🔍 **Cloud Run Constraints & Solutions**

Cloud Run is a serverless platform with specific limitations that affect how we implement background tasks:

### **Constraints:**
- ❌ No persistent processes (services can scale to zero)
- ❌ No systemd services or cron jobs
- ❌ 15-minute maximum request timeout
- ❌ No local file storage for logs/data
- ❌ Limited to HTTP-triggered services

### **Solutions:**
- ✅ Use Cloud Scheduler + HTTP endpoints for periodic tasks
- ✅ Separate worker service for background processing
- ✅ Google Cloud Logging for centralized logs
- ✅ Redis for message queuing
- ✅ Cloud SQL for persistence

## 🏗️ **Cloud Run Architecture**

```
Cloud Scheduler → HTTP Triggers → Cloud Run Workers → Redis → Database
     ↓               ↓                  ↓           ↓         ↓
Periodic Tasks → REST Endpoints → Background Jobs → Queue → Notifications
Health Checks → Status API → Task Processing → Results → Email Delivery
```

## 📝 **Implementation Strategy**

### **Option 1: HTTP-Triggered Background Tasks (Recommended)**

Instead of Celery Beat, use Cloud Scheduler to trigger HTTP endpoints that queue background tasks.

### **Option 2: Dedicated Worker Service**

Deploy a separate Cloud Run service specifically for background processing.

### **Option 3: Hybrid Approach**

Combine Cloud Scheduler for periodic triggers with Cloud Tasks for reliable execution.

## 🚀 **Implementation Steps**

### **Step 1: Deploy Background Worker Service**

```bash
# 1. Deploy the worker service
./scripts/gcloud/deploy_worker_cloud_run.sh

# 2. Update environment variables
./scripts/gcloud/update_worker_env.sh

# 3. Set up Cloud Scheduler jobs
./scripts/gcloud/setup_cloud_scheduler.sh
```

### **Step 2: Test the Implementation**

```bash
# Get worker service URL
WORKER_URL=$(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)')

# Test health endpoint
curl "$WORKER_URL/health"

# Test detailed health check
curl "$WORKER_URL/health/detailed"

# Test task execution
curl -X POST "$WORKER_URL/tasks/execute" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "health_check_congress_api", "parameters": {}}'
```

### **Step 3: Monitor and Manage**

```bash
# View Cloud Scheduler jobs
gcloud scheduler jobs list --location=us-west1

# Trigger a job manually
gcloud scheduler jobs run health-checks --location=us-west1

# View worker logs
gcloud run logs read --service=capitolscope-worker --region=us-west1

# Monitor job execution
gcloud logging read "resource.type=cloud_scheduler_job" --limit=10
```

## 📋 **Files Created**

### **Core Worker Service**
- `app/src/background/cloud_run_worker.py` - FastAPI service for background tasks
- `Dockerfile.worker` - Docker configuration for worker service

### **Deployment Scripts**
- `scripts/gcloud/deploy_worker_cloud_run.sh` - Deploy worker to Cloud Run
- `scripts/gcloud/update_worker_env.sh` - Update worker environment variables
- `scripts/gcloud/setup_cloud_scheduler.sh` - Create Cloud Scheduler jobs

## 🔧 **Configuration Details**

### **Worker Service Configuration**
- **CPU**: 2 vCPU
- **Memory**: 1 GB
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 10
- **Timeout**: 15 minutes
- **Concurrency**: 10 requests

### **Cloud Scheduler Jobs**
| Job | Schedule | Description |
|-----|----------|-------------|
| congressional-data-sync | Every 2 hours (business hours) | Sync congressional data |
| stock-price-updates | Every 15 minutes (market hours) | Update stock prices |
| notification-processing | Every 30 minutes | Process notifications |
| health-checks | Every 10 minutes | System health monitoring |
| daily-maintenance | Daily at 2 AM UTC | Comprehensive maintenance |

### **API Endpoints**

#### **Health & Monitoring**
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies
- `GET /admin/queue-status` - Queue and Redis status
- `GET /admin/recent-tasks` - Recent task history

#### **Task Execution**
- `POST /tasks/execute` - Execute task immediately
- `GET /tasks/{task_id}/status` - Get task status

#### **Scheduled Tasks (Cloud Scheduler)**
- `POST /scheduled/congressional-sync` - Congressional data sync
- `POST /scheduled/stock-prices` - Stock price updates
- `POST /scheduled/notifications` - Notification processing
- `POST /scheduled/health-check` - Health checks

## 🎯 **Benefits of Cloud Run Implementation**

### **Cost Efficiency**
- ✅ Pay only for actual usage
- ✅ Scales to zero when idle
- ✅ No infrastructure management

### **Reliability**
- ✅ Automatic scaling based on demand
- ✅ Built-in health checks and restart
- ✅ Global load balancing

### **Observability**
- ✅ Integrated with Google Cloud Logging
- ✅ Cloud Monitoring and alerting
- ✅ Request tracing and debugging

### **Security**
- ✅ Automatic SSL/TLS termination
- ✅ IAM-based access control
- ✅ VPC integration available

## 🔄 **Migration from Traditional Celery**

### **What Changes**
- ❌ No Celery Beat (replaced by Cloud Scheduler)
- ❌ No systemd services (replaced by Cloud Run)
- ❌ No local file storage (use Cloud Storage if needed)
- ✅ Same task logic and Redis queuing
- ✅ Same notification system
- ✅ Same database operations

### **What Stays the Same**
- ✅ All existing task functions
- ✅ Database operations
- ✅ Redis for caching and queuing
- ✅ Email notifications
- ✅ Congressional data processing

## 📊 **Monitoring Dashboard**

Once deployed, you can monitor your system through:

1. **Cloud Run Console**: Monitor service health and traffic
2. **Cloud Scheduler Console**: View job execution history
3. **Cloud Logging**: Centralized log viewing and search
4. **Worker Health Endpoint**: Real-time system status

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Worker service not starting**
   ```bash
   # Check logs
   gcloud run logs read --service=capitolscope-worker --region=us-west1
   
   # Check environment variables
   gcloud run services describe capitolscope-worker --region=us-west1
   ```

2. **Scheduler jobs failing**
   ```bash
   # Check job status
   gcloud scheduler jobs describe JOB_NAME --location=us-west1
   
   # View execution logs
   gcloud logging read "resource.type=cloud_scheduler_job" --limit=10
   ```

3. **Database connection issues**
   ```bash
   # Test from worker
   curl -X POST "WORKER_URL/tasks/execute" \
     -H "Content-Type: application/json" \
     -d '{"task_name": "system_health_check"}'
   ```

### **Performance Optimization**

1. **Increase worker resources for heavy tasks**
   ```bash
   gcloud run services update capitolscope-worker \
     --region=us-west1 \
     --cpu=4 \
     --memory=2Gi
   ```

2. **Adjust scheduler frequency based on usage**
   ```bash
   # Update job schedule
   gcloud scheduler jobs update http stock-price-updates \
     --location=us-west1 \
     --schedule="*/30 9-16 * * MON-FRI"
   ```

## 🎉 **Ready for Production**

Your Cloud Run scheduler implementation is now ready to:

- ✅ Handle Kyle's MTG alerts reliably
- ✅ Scale automatically based on demand
- ✅ Process congressional data updates
- ✅ Send email notifications
- ✅ Monitor system health
- ✅ Scale to thousands of users

The system provides the same functionality as the traditional Celery implementation but optimized for serverless Cloud Run deployment!

