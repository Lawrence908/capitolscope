# 🌐 CapitolScope Cloud Run Scheduler - Deployment Summary

## 🎯 **Quick Deployment Guide**

Follow these steps to deploy the background scheduler system to your live Cloud Run environment:

### **Prerequisites**
- ✅ Existing Cloud Run API service deployed
- ✅ Redis instance (Supabase or Google Cloud Memorystore)
- ✅ Environment variables configured
- ✅ Google Cloud CLI installed and authenticated

### **Step-by-Step Deployment**

```bash
# 1. Deploy the background worker service
./scripts/gcloud/deploy_worker_cloud_run.sh

# 2. Configure environment variables
./scripts/gcloud/update_worker_env.sh

# 3. Set up Cloud Scheduler jobs
./scripts/gcloud/setup_cloud_scheduler.sh

# 4. Test the deployment
WORKER_URL=$(gcloud run services describe capitolscope-worker --region=us-west1 --format='value(status.url)')
curl "$WORKER_URL/health/detailed"
```

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Cloud Scheduler │───▶│ Worker Service   │───▶│ Redis Queue     │
│ (Periodic Jobs) │    │ (Cloud Run)      │    │ (Task Storage)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ API Service     │◀───│ Database         │◀───│ Background      │
│ (Main App)      │    │ (Supabase)       │    │ Processing      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Frontend        │    │ Trade Data       │    │ Email           │
│ (Users)         │    │ (Congressional)  │    │ Notifications   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 **Services Deployed**

### **1. Main API Service** (Existing)
- **Service**: `capitolscope-api`
- **Purpose**: Handle user requests, serve frontend
- **URL**: `https://capitolscope-api-*.us-west1.run.app`

### **2. Background Worker Service** (New)
- **Service**: `capitolscope-worker`
- **Purpose**: Process background tasks, handle scheduled jobs
- **URL**: `https://capitolscope-worker-*.us-west1.run.app`

### **3. Cloud Scheduler Jobs** (New)
- **congressional-data-sync**: Every 2 hours during business hours
- **stock-price-updates**: Every 15 minutes during market hours
- **notification-processing**: Every 30 minutes
- **health-checks**: Every 10 minutes
- **daily-maintenance**: Daily at 2 AM UTC

## 🔧 **Configuration**

### **Worker Service Settings**
```yaml
CPU: 2 vCPU
Memory: 1 GB
Min Instances: 0
Max Instances: 10
Timeout: 15 minutes
Concurrency: 10
```

### **Environment Variables**
The worker service uses the same environment variables as your main API service:
- Database connection (Supabase)
- Redis connection
- API keys (Alpha Vantage, Polygon, etc.)
- Email configuration
- Application settings

## 📊 **Monitoring & Management**

### **Health Monitoring**
```bash
# Basic health check
curl https://capitolscope-worker-*.us-west1.run.app/health

# Detailed health check
curl https://capitolscope-worker-*.us-west1.run.app/health/detailed

# Queue status
curl https://capitolscope-worker-*.us-west1.run.app/admin/queue-status
```

### **Cloud Console Monitoring**
1. **Cloud Run Console**: `https://console.cloud.google.com/run`
2. **Cloud Scheduler Console**: `https://console.cloud.google.com/cloudscheduler`
3. **Cloud Logging Console**: `https://console.cloud.google.com/logs`

### **Manual Task Execution**
```bash
# Execute a task manually
curl -X POST https://capitolscope-worker-*.us-west1.run.app/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "process_pending_notifications",
    "parameters": {},
    "priority": 5
  }'

# Check task status
curl https://capitolscope-worker-*.us-west1.run.app/tasks/TASK_ID/status
```

### **Scheduler Management**
```bash
# List all scheduler jobs
gcloud scheduler jobs list --location=us-west1

# Trigger a job manually
gcloud scheduler jobs run congressional-data-sync --location=us-west1

# Pause a job
gcloud scheduler jobs pause stock-price-updates --location=us-west1

# Resume a job
gcloud scheduler jobs resume stock-price-updates --location=us-west1
```

## 💡 **Key Benefits vs Traditional Celery**

### **Cost Efficiency**
- **Traditional**: Fixed server costs 24/7
- **Cloud Run**: Pay only for actual execution time
- **Savings**: 60-80% cost reduction for typical workloads

### **Scalability**
- **Traditional**: Manual scaling, resource planning
- **Cloud Run**: Automatic scaling 0-10 instances
- **Benefit**: Handle traffic spikes automatically

### **Maintenance**
- **Traditional**: Server management, OS updates, monitoring setup
- **Cloud Run**: Fully managed, automatic updates
- **Benefit**: Focus on application logic, not infrastructure

### **Reliability**
- **Traditional**: Single point of failure
- **Cloud Run**: Multi-zone deployment, automatic restarts
- **Benefit**: 99.95% SLA with automatic failover

## 🔍 **Task Execution Flow**

1. **Cloud Scheduler** triggers HTTP endpoint on schedule
2. **Worker Service** receives request and queues task
3. **Background Processor** executes task asynchronously
4. **Task Result** stored in Redis for status tracking
5. **Logging** captured in Google Cloud Logging

## 📈 **Performance Expectations**

### **Task Execution Times**
- **Health Checks**: 5-10 seconds
- **Notification Processing**: 30-60 seconds
- **Stock Price Updates**: 2-5 minutes
- **Congressional Data Sync**: 5-15 minutes
- **Daily Maintenance**: 10-30 minutes

### **Scaling Behavior**
- **Cold Start**: 2-5 seconds for first request
- **Warm Instances**: <100ms response time
- **Concurrent Tasks**: Up to 10 simultaneous executions
- **Auto-scaling**: Scales up within 30 seconds

## 🚨 **Troubleshooting**

### **Common Issues & Solutions**

1. **Worker Service Not Responding**
   ```bash
   # Check service status
   gcloud run services describe capitolscope-worker --region=us-west1
   
   # View logs
   gcloud run logs read --service=capitolscope-worker --region=us-west1 --limit=50
   ```

2. **Scheduler Jobs Failing**
   ```bash
   # Check job execution history
   gcloud scheduler jobs describe congressional-data-sync --location=us-west1
   
   # View scheduler logs
   gcloud logging read "resource.type=cloud_scheduler_job" --limit=20
   ```

3. **Database Connection Issues**
   ```bash
   # Test database connectivity
   curl -X POST https://capitolscope-worker-*.us-west1.run.app/tasks/execute \
     -H "Content-Type: application/json" \
     -d '{"task_name": "system_health_check"}'
   ```

4. **Redis Connection Issues**
   ```bash
   # Check Redis status in health endpoint
   curl https://capitolscope-worker-*.us-west1.run.app/health/detailed
   ```

### **Performance Tuning**

1. **Increase Resources for Heavy Tasks**
   ```bash
   gcloud run services update capitolscope-worker \
     --region=us-west1 \
     --cpu=4 \
     --memory=2Gi
   ```

2. **Adjust Concurrency**
   ```bash
   gcloud run services update capitolscope-worker \
     --region=us-west1 \
     --concurrency=20
   ```

3. **Optimize Scheduler Frequency**
   ```bash
   # Less frequent updates during off-hours
   gcloud scheduler jobs update http stock-price-updates \
     --location=us-west1 \
     --schedule="*/30 9-16 * * MON-FRI"
   ```

## 🎉 **Deployment Complete!**

Your CapitolScope scheduler system is now running on Cloud Run with:

✅ **Automated background processing** for trade alerts  
✅ **Scalable architecture** that handles demand spikes  
✅ **Cost-effective operation** with pay-per-use pricing  
✅ **Comprehensive monitoring** and health checks  
✅ **Reliable notification delivery** for users  
✅ **Easy management** through Google Cloud Console  

The system will now automatically:
- Sync congressional trading data
- Update stock prices during market hours
- Process and send trade alert notifications
- Monitor system health and performance
- Perform daily maintenance tasks

Kyle's MTG alerts (and any future user alerts) will be processed reliably with this serverless, auto-scaling infrastructure! 🚀



