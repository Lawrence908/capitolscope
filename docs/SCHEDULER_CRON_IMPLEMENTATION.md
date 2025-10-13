# ⏰ Scheduler & Cron Implementation Plan for Trade Alerts

## 📋 **Project Overview**

**Goal:** Implement a robust scheduling system for running background tasks on your live server, specifically for trade alert processing, data ingestion, and notification delivery.

**Key Components:**
- Celery worker processes
- Redis task queue
- Cron jobs for periodic tasks
- Process monitoring and health checks
- Error handling and retry logic

---

## 🏗️ **Architecture Overview**

```
Cron Scheduler → Celery Beat → Redis Queue → Celery Workers → Database/Email
      ↓             ↓            ↓             ↓               ↓
Data Ingestion → Task Queue → Background → Process Trade → Send Notifications
Alert Checks   → Scheduling  → Processing  → Evaluation    → Email Delivery
Health Checks  → Periodic    → Async Exec  → Rule Engine   → Status Tracking
```

---

## 📁 **Implementation Structure**

### **Phase 1: Celery Production Setup (1 day)**

#### **1.1 Production Celery Configuration**
```python
# File: app/src/background/production_celery.py
```

**Purpose:** Production-ready Celery configuration with proper error handling, monitoring, and logging.

#### **1.2 Worker Management Scripts**
```bash
# File: scripts/celery_management.sh
```

**Purpose:** Scripts to start, stop, restart, and monitor Celery workers and beat scheduler.

#### **1.3 Systemd Service Files**
```ini
# File: deploy/systemd/capitolscope-celery-worker.service
# File: deploy/systemd/capitolscope-celery-beat.service
```

**Purpose:** System service definitions for automatic startup and process management.

### **Phase 2: Task Scheduling (1 day)**

#### **2.1 Enhanced Celery Beat Configuration**
```python
# File: app/src/background/beat_schedule.py
```

**Purpose:** Comprehensive task scheduling with different intervals and priorities.

#### **2.2 Cron Job Integration**
```bash
# File: deploy/cron/capitolscope-tasks.cron
```

**Purpose:** System-level cron jobs for critical tasks and health checks.

#### **2.3 Task Monitoring**
```python
# File: app/src/background/monitoring.py
```

**Purpose:** Health checks, task monitoring, and failure alerting.

---

## 🔧 **Detailed Implementation**

### **Step 1: Production Celery Configuration**

```python
# app/src/background/production_celery.py

import os
import logging
from celery import Celery
from celery.signals import setup_logging, worker_ready, worker_shutdown
from core.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/capitolscope/celery.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create Celery app with production settings
celery_app = Celery(
    "capitolscope",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['background.tasks']
)

# Production Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'background.tasks.process_new_trade_notifications': {'queue': 'notifications'},
        'background.tasks.sync_congressional_trades': {'queue': 'data_ingestion'},
        'background.tasks.update_stock_prices': {'queue': 'price_updates'},
        'background.tasks.cleanup_old_data': {'queue': 'maintenance'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {'routing_key': 'default'},
        'notifications': {'routing_key': 'notifications'},
        'data_ingestion': {'routing_key': 'data_ingestion'},
        'price_updates': {'routing_key': 'price_updates'},
        'maintenance': {'routing_key': 'maintenance'},
    },
    
    # Worker configuration
    worker_concurrency=4,  # Adjust based on server resources
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task execution
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task timeouts and retries
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
    },
    
    # Monitoring
    task_send_sent_event=True,
    task_track_started=True,
    worker_send_task_events=True,
    
    # Security
    task_always_eager=False,  # Never True in production
    task_store_eager_result=False,
)

# Enhanced beat schedule for production
celery_app.conf.beat_schedule = {
    # Data ingestion - every 2 hours during business hours
    'sync-congressional-trades': {
        'task': 'background.tasks.sync_congressional_trades',
        'schedule': 7200.0,  # 2 hours
        'options': {'queue': 'data_ingestion', 'priority': 8}
    },
    
    # Stock price updates - every 15 minutes during market hours
    'update-stock-prices': {
        'task': 'background.tasks.update_stock_prices',
        'schedule': 900.0,  # 15 minutes
        'options': {'queue': 'price_updates', 'priority': 6}
    },
    
    # Notification processing - every 30 minutes
    'process-pending-notifications': {
        'task': 'background.tasks.process_pending_notifications',
        'schedule': 1800.0,  # 30 minutes
        'options': {'queue': 'notifications', 'priority': 9}
    },
    
    # Health checks - every 5 minutes
    'system-health-check': {
        'task': 'background.tasks.system_health_check',
        'schedule': 300.0,  # 5 minutes
        'options': {'queue': 'default', 'priority': 5}
    },
    
    # Daily maintenance - 2 AM UTC
    'daily-maintenance': {
        'task': 'background.tasks.daily_maintenance',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'maintenance', 'priority': 3}
    },
    
    # Weekly cleanup - Sunday 3 AM UTC
    'weekly-cleanup': {
        'task': 'background.tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {'queue': 'maintenance', 'priority': 2}
    },
}

@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery."""
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': '/var/log/capitolscope/celery.log',
                'formatter': 'verbose',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'celery': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': True,
            },
            'background': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    })

@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Log when worker is ready."""
    logger.info("Celery worker is ready and waiting for tasks")

@worker_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """Log when worker is shutting down."""
    logger.info("Celery worker is shutting down")

if __name__ == '__main__':
    celery_app.start()
```

### **Step 2: Systemd Service Files**

```ini
# deploy/systemd/capitolscope-celery-worker.service

[Unit]
Description=CapitolScope Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=capitolscope
Group=capitolscope
WorkingDirectory=/opt/capitolscope
Environment=PYTHONPATH=/opt/capitolscope/app/src
ExecStart=/opt/capitolscope/.venv/bin/celery -A background.production_celery worker \
    --loglevel=info \
    --logfile=/var/log/capitolscope/celery-worker.log \
    --pidfile=/var/run/capitolscope/celery-worker.pid \
    --concurrency=4 \
    --queues=default,notifications,data_ingestion,price_updates,maintenance
ExecStop=/bin/kill -TERM $MAINPID
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
MemoryLimit=2G
CPUQuota=200%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/capitolscope /var/run/capitolscope /tmp

[Install]
WantedBy=multi-user.target
```

```ini
# deploy/systemd/capitolscope-celery-beat.service

[Unit]
Description=CapitolScope Celery Beat Scheduler
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=capitolscope
Group=capitolscope
WorkingDirectory=/opt/capitolscope
Environment=PYTHONPATH=/opt/capitolscope/app/src
ExecStart=/opt/capitolscope/.venv/bin/celery -A background.production_celery beat \
    --loglevel=info \
    --logfile=/var/log/capitolscope/celery-beat.log \
    --pidfile=/var/run/capitolscope/celery-beat.pid \
    --schedule=/var/lib/capitolscope/celerybeat-schedule
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryLimit=512M

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/capitolscope /var/run/capitolscope /var/lib/capitolscope

[Install]
WantedBy=multi-user.target
```

### **Step 3: Management Scripts**

```bash
#!/bin/bash
# scripts/celery_management.sh

set -e

CELERY_APP="background.production_celery"
CELERY_USER="capitolscope"
CELERY_GROUP="capitolscope"
CELERY_VENV="/opt/capitolscope/.venv"
CELERY_CHDIR="/opt/capitolscope"
LOG_DIR="/var/log/capitolscope"
PID_DIR="/var/run/capitolscope"

# Ensure directories exist
sudo mkdir -p $LOG_DIR $PID_DIR /var/lib/capitolscope
sudo chown $CELERY_USER:$CELERY_GROUP $LOG_DIR $PID_DIR /var/lib/capitolscope

case "$1" in
    start-worker)
        echo "Starting Celery worker..."
        sudo systemctl start capitolscope-celery-worker
        sudo systemctl enable capitolscope-celery-worker
        ;;
    
    start-beat)
        echo "Starting Celery beat..."
        sudo systemctl start capitolscope-celery-beat
        sudo systemctl enable capitolscope-celery-beat
        ;;
    
    start-all)
        echo "Starting all Celery services..."
        $0 start-worker
        $0 start-beat
        ;;
    
    stop-worker)
        echo "Stopping Celery worker..."
        sudo systemctl stop capitolscope-celery-worker
        ;;
    
    stop-beat)
        echo "Stopping Celery beat..."
        sudo systemctl stop capitolscope-celery-beat
        ;;
    
    stop-all)
        echo "Stopping all Celery services..."
        $0 stop-worker
        $0 stop-beat
        ;;
    
    restart-worker)
        echo "Restarting Celery worker..."
        sudo systemctl restart capitolscope-celery-worker
        ;;
    
    restart-beat)
        echo "Restarting Celery beat..."
        sudo systemctl restart capitolscope-celery-beat
        ;;
    
    restart-all)
        echo "Restarting all Celery services..."
        $0 restart-worker
        $0 restart-beat
        ;;
    
    status)
        echo "=== Celery Services Status ==="
        sudo systemctl status capitolscope-celery-worker --no-pager
        echo ""
        sudo systemctl status capitolscope-celery-beat --no-pager
        ;;
    
    logs-worker)
        echo "=== Celery Worker Logs ==="
        sudo journalctl -u capitolscope-celery-worker -f
        ;;
    
    logs-beat)
        echo "=== Celery Beat Logs ==="
        sudo journalctl -u capitolscope-celery-beat -f
        ;;
    
    monitor)
        echo "=== Celery Task Monitor ==="
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        celery -A $CELERY_APP flower --port=5555 --basic_auth=admin:secure_password
        ;;
    
    purge)
        echo "Purging all tasks from queue..."
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        celery -A $CELERY_APP purge -f
        ;;
    
    inspect)
        echo "=== Active Tasks ==="
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        celery -A $CELERY_APP inspect active
        echo ""
        echo "=== Scheduled Tasks ==="
        celery -A $CELERY_APP inspect scheduled
        echo ""
        echo "=== Worker Stats ==="
        celery -A $CELERY_APP inspect stats
        ;;
    
    test)
        echo "Testing task execution..."
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        python -c "
from background.tasks import system_health_check
result = system_health_check.delay()
print(f'Task ID: {result.id}')
print(f'Result: {result.get(timeout=30)}')
"
        ;;
    
    *)
        echo "Usage: $0 {start-all|stop-all|restart-all|start-worker|stop-worker|restart-worker|start-beat|stop-beat|restart-beat|status|logs-worker|logs-beat|monitor|purge|inspect|test}"
        exit 1
        ;;
esac

exit 0
```

### **Step 4: Cron Job Configuration**

```bash
# deploy/cron/capitolscope-tasks.cron
# Copy to /etc/cron.d/capitolscope-tasks

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=admin@capitolscope.chrislawrence.ca

# Health check every 5 minutes
*/5 * * * * capitolscope /opt/capitolscope/scripts/health_check.sh >> /var/log/capitolscope/health_check.log 2>&1

# Backup critical data daily at 1 AM
0 1 * * * capitolscope /opt/capitolscope/scripts/backup_data.sh >> /var/log/capitolscope/backup.log 2>&1

# Clean up old log files weekly
0 0 * * 0 capitolscope find /var/log/capitolscope -name "*.log" -mtime +7 -delete

# Check disk space every hour
0 * * * * capitolscope /opt/capitolscope/scripts/disk_space_check.sh >> /var/log/capitolscope/disk_check.log 2>&1

# Monitor Celery workers every 10 minutes
*/10 * * * * capitolscope /opt/capitolscope/scripts/celery_health_check.sh >> /var/log/capitolscope/celery_health.log 2>&1
```

### **Step 5: Health Check Scripts**

```bash
#!/bin/bash
# scripts/health_check.sh

CELERY_APP="background.production_celery"
CELERY_VENV="/opt/capitolscope/.venv"
CELERY_CHDIR="/opt/capitolscope"
LOG_FILE="/var/log/capitolscope/health_check.log"

echo "$(date): Starting health check..." >> $LOG_FILE

# Check if services are running
if ! systemctl is-active --quiet capitolscope-celery-worker; then
    echo "$(date): ERROR - Celery worker is not running" >> $LOG_FILE
    # Restart worker
    systemctl restart capitolscope-celery-worker
    echo "$(date): Restarted Celery worker" >> $LOG_FILE
fi

if ! systemctl is-active --quiet capitolscope-celery-beat; then
    echo "$(date): ERROR - Celery beat is not running" >> $LOG_FILE
    # Restart beat
    systemctl restart capitolscope-celery-beat
    echo "$(date): Restarted Celery beat" >> $LOG_FILE
fi

# Check Redis connection
if ! redis-cli ping > /dev/null 2>&1; then
    echo "$(date): ERROR - Redis is not responding" >> $LOG_FILE
    exit 1
fi

# Check PostgreSQL connection
if ! sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1; then
    echo "$(date): ERROR - PostgreSQL is not responding" >> $LOG_FILE
    exit 1
fi

# Test task execution
cd $CELERY_CHDIR
source $CELERY_VENV/bin/activate

if ! timeout 30 python -c "
from background.tasks import system_health_check
result = system_health_check.delay()
result.get(timeout=25)
" > /dev/null 2>&1; then
    echo "$(date): ERROR - Task execution test failed" >> $LOG_FILE
    exit 1
fi

echo "$(date): Health check completed successfully" >> $LOG_FILE
```

---

## 🚀 **Deployment Guide**

### **Step 1: Server Setup**
```bash
# Install required packages
sudo apt update
sudo apt install redis-server postgresql nginx supervisor

# Create user and directories
sudo useradd -m -s /bin/bash capitolscope
sudo mkdir -p /opt/capitolscope /var/log/capitolscope /var/run/capitolscope /var/lib/capitolscope
sudo chown capitolscope:capitolscope /opt/capitolscope /var/log/capitolscope /var/run/capitolscope /var/lib/capitolscope

# Clone and setup application
sudo -u capitolscope git clone https://github.com/your-repo/CapitolScope.git /opt/capitolscope
cd /opt/capitolscope
sudo -u capitolscope python -m venv .venv
sudo -u capitolscope .venv/bin/pip install -r requirements.txt
```

### **Step 2: Service Installation**
```bash
# Copy systemd service files
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Copy cron jobs
sudo cp deploy/cron/capitolscope-tasks.cron /etc/cron.d/

# Make scripts executable
chmod +x scripts/*.sh

# Start services
./scripts/celery_management.sh start-all
```

### **Step 3: Monitoring Setup**
```bash
# Install Flower for task monitoring (optional)
.venv/bin/pip install flower

# Start monitoring dashboard
./scripts/celery_management.sh monitor
# Access at http://your-server:5555
```

---

## 📊 **Monitoring & Alerting**

### **Key Metrics to Monitor**
- Task execution rates and success/failure ratios
- Queue sizes and processing times
- Worker memory and CPU usage
- Database connection pool status
- Email delivery rates

### **Alert Conditions**
- Worker process down for > 5 minutes
- Task failure rate > 10%
- Queue backlog > 100 tasks
- High memory usage > 80%
- Disk space < 10%

This implementation provides a robust, production-ready scheduling system that can handle Kyle's MTG alerts and scale to thousands of users! 🎯



