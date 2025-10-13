#!/bin/bash
# Celery Worker Health Check
# Monitors Celery worker status and task queue health

CELERY_APP="background.production_celery"
CELERY_VENV="/opt/capitolscope/.venv"
CELERY_CHDIR="/opt/capitolscope"
LOG_FILE="/var/log/capitolscope/celery_health.log"

echo "$(date): Starting Celery health check..." >> $LOG_FILE

cd $CELERY_CHDIR
source $CELERY_VENV/bin/activate

# Check if workers are responding
WORKER_STATUS=$(celery -A $CELERY_APP inspect ping 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "$(date): ERROR - Celery workers not responding to ping" >> $LOG_FILE
    # Restart worker service
    systemctl restart capitolscope-celery-worker
    echo "$(date): Restarted Celery worker service" >> $LOG_FILE
    exit 1
fi

# Check queue lengths
python -c "
import redis
import sys
import os
sys.path.append('app/src')

try:
    from core.config import get_settings
    settings = get_settings()
    redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    
    queues = ['default', 'notifications', 'data_ingestion', 'price_updates', 'maintenance', 'health_checks']
    warning_threshold = 100
    critical_threshold = 500
    
    warnings = []
    criticals = []
    
    for queue in queues:
        queue_key = f'celery:{queue}'
        length = redis_client.llen(queue_key)
        
        if length > critical_threshold:
            criticals.append(f'{queue}: {length}')
        elif length > warning_threshold:
            warnings.append(f'{queue}: {length}')
    
    if criticals:
        print(f'CRITICAL - Queue backlog: {criticals}')
        sys.exit(2)
    elif warnings:
        print(f'WARNING - Queue backlog: {warnings}')
        sys.exit(1)
    else:
        print('OK - Queue lengths normal')
        sys.exit(0)
        
except Exception as e:
    print(f'ERROR - Queue check failed: {e}')
    sys.exit(2)
" >> $LOG_FILE 2>&1

QUEUE_CHECK_EXIT=$?
if [ $QUEUE_CHECK_EXIT -eq 2 ]; then
    echo "$(date): CRITICAL - Queue backlog detected" >> $LOG_FILE
    exit 1
elif [ $QUEUE_CHECK_EXIT -eq 1 ]; then
    echo "$(date): WARNING - Queue backlog detected" >> $LOG_FILE
fi

# Check for failed tasks in the last hour
FAILED_TASKS=$(python -c "
import sys
sys.path.append('app/src')
from celery import Celery
from background.production_celery import celery_app

try:
    # This is a simplified check - in production you might want to 
    # query a task result backend or monitoring system
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    
    if stats:
        for worker, data in stats.items():
            rusage = data.get('rusage', {})
            total_tasks = data.get('total', {})
            
            # Check if worker is processing tasks normally
            if total_tasks:
                print('Workers processing tasks normally')
                break
    else:
        print('No worker stats available')
        
except Exception as e:
    print(f'Error checking task stats: {e}')
")

echo "$(date): Task status: $FAILED_TASKS" >> $LOG_FILE
echo "$(date): Celery health check completed" >> $LOG_FILE



