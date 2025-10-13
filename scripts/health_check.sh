#!/bin/bash
# CapitolScope System Health Check
# Comprehensive health monitoring for all system components

CELERY_APP="background.production_celery"
CELERY_VENV="/opt/capitolscope/.venv"
CELERY_CHDIR="/opt/capitolscope"
LOG_FILE="/var/log/capitolscope/health_check.log"

echo "$(date): Starting comprehensive health check..." >> $LOG_FILE

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
    # Try to restart Redis
    systemctl restart redis
    echo "$(date): Attempted Redis restart" >> $LOG_FILE
    exit 1
fi

# Check PostgreSQL connection
if ! sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1; then
    echo "$(date): ERROR - PostgreSQL is not responding" >> $LOG_FILE
    # Try to restart PostgreSQL
    systemctl restart postgresql
    echo "$(date): Attempted PostgreSQL restart" >> $LOG_FILE
    exit 1
fi

# Check disk space (warn if < 20%, critical if < 10%)
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): CRITICAL - Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
    exit 1
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): WARNING - Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    echo "$(date): CRITICAL - Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
elif [ "$MEMORY_USAGE" -gt 80 ]; then
    echo "$(date): WARNING - Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
fi

# Test task execution
cd $CELERY_CHDIR
source $CELERY_VENV/bin/activate

if ! timeout 30 python -c "
import sys
sys.path.append('app/src')
from background.tasks import system_health_check
result = system_health_check.delay()
result.get(timeout=25)
" > /dev/null 2>&1; then
    echo "$(date): ERROR - Task execution test failed" >> $LOG_FILE
    exit 1
fi

# Check application endpoints (if running)
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "$(date): Application health endpoint OK" >> $LOG_FILE
else
    echo "$(date): WARNING - Application health endpoint not responding" >> $LOG_FILE
fi

echo "$(date): Health check completed successfully" >> $LOG_FILE



