#!/bin/bash
# CapitolScope Celery Management Script
# Provides comprehensive management of Celery workers and beat scheduler

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
        echo "Celery worker started and enabled"
        ;;
    
    start-beat)
        echo "Starting Celery beat..."
        sudo systemctl start capitolscope-celery-beat
        sudo systemctl enable capitolscope-celery-beat
        echo "Celery beat started and enabled"
        ;;
    
    start-all)
        echo "Starting all Celery services..."
        $0 start-worker
        $0 start-beat
        echo "All Celery services started"
        ;;
    
    stop-worker)
        echo "Stopping Celery worker..."
        sudo systemctl stop capitolscope-celery-worker
        echo "Celery worker stopped"
        ;;
    
    stop-beat)
        echo "Stopping Celery beat..."
        sudo systemctl stop capitolscope-celery-beat
        echo "Celery beat stopped"
        ;;
    
    stop-all)
        echo "Stopping all Celery services..."
        $0 stop-worker
        $0 stop-beat
        echo "All Celery services stopped"
        ;;
    
    restart-worker)
        echo "Restarting Celery worker..."
        sudo systemctl restart capitolscope-celery-worker
        echo "Celery worker restarted"
        ;;
    
    restart-beat)
        echo "Restarting Celery beat..."
        sudo systemctl restart capitolscope-celery-beat
        echo "Celery beat restarted"
        ;;
    
    restart-all)
        echo "Restarting all Celery services..."
        $0 restart-worker
        $0 restart-beat
        echo "All Celery services restarted"
        ;;
    
    status)
        echo "=== Celery Services Status ==="
        echo "Worker Service:"
        sudo systemctl status capitolscope-celery-worker --no-pager || true
        echo ""
        echo "Beat Service:"
        sudo systemctl status capitolscope-celery-beat --no-pager || true
        ;;
    
    logs-worker)
        echo "=== Celery Worker Logs ==="
        sudo journalctl -u capitolscope-celery-worker -f
        ;;
    
    logs-beat)
        echo "=== Celery Beat Logs ==="
        sudo journalctl -u capitolscope-celery-beat -f
        ;;
    
    logs-all)
        echo "=== Recent Celery Logs ==="
        echo "Worker logs (last 50 lines):"
        sudo journalctl -u capitolscope-celery-worker -n 50 --no-pager
        echo ""
        echo "Beat logs (last 50 lines):"
        sudo journalctl -u capitolscope-celery-beat -n 50 --no-pager
        ;;
    
    monitor)
        echo "=== Celery Task Monitor ==="
        echo "Starting Flower monitoring dashboard..."
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        echo "Flower will be available at http://localhost:5555"
        echo "Default credentials: admin / secure_password"
        celery -A $CELERY_APP flower --port=5555 --basic_auth=admin:secure_password
        ;;
    
    purge)
        echo "WARNING: This will purge all tasks from the queue!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Purging all tasks from queue..."
            cd $CELERY_CHDIR
            source $CELERY_VENV/bin/activate
            celery -A $CELERY_APP purge -f
            echo "Queue purged successfully"
        else
            echo "Operation cancelled"
        fi
        ;;
    
    inspect)
        echo "=== Celery Worker Inspection ==="
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        
        echo "Active Tasks:"
        celery -A $CELERY_APP inspect active || echo "No active tasks or workers not responding"
        
        echo ""
        echo "Scheduled Tasks:"
        celery -A $CELERY_APP inspect scheduled || echo "No scheduled tasks or workers not responding"
        
        echo ""
        echo "Worker Stats:"
        celery -A $CELERY_APP inspect stats || echo "No stats available or workers not responding"
        
        echo ""
        echo "Registered Tasks:"
        celery -A $CELERY_APP inspect registered || echo "No registered tasks or workers not responding"
        ;;
    
    test)
        echo "Testing task execution..."
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        
        echo "Submitting test health check task..."
        python -c "
import sys
sys.path.append('app/src')
from background.tasks import system_health_check
try:
    result = system_health_check.delay()
    print(f'Task submitted successfully. Task ID: {result.id}')
    print('Waiting for result (timeout: 30 seconds)...')
    result_data = result.get(timeout=30)
    print(f'Task completed successfully!')
    print(f'Result: {result_data}')
except Exception as e:
    print(f'Task execution failed: {e}')
    sys.exit(1)
"
        ;;
    
    queue-status)
        echo "=== Queue Status ==="
        cd $CELERY_CHDIR
        source $CELERY_VENV/bin/activate
        
        # Check queue lengths
        python -c "
import redis
import json
from celery import Celery
from background.production_celery import celery_app

try:
    # Connect to Redis
    redis_client = redis.Redis.from_url('$CELERY_BROKER_URL')
    
    queues = ['default', 'notifications', 'data_ingestion', 'price_updates', 'maintenance', 'health_checks']
    
    print('Queue Lengths:')
    print('-' * 40)
    for queue in queues:
        queue_key = f'celery:{queue}'
        length = redis_client.llen(queue_key)
        print(f'{queue:20}: {length:4} tasks')
    
    print()
    print('Redis Info:')
    print('-' * 40)
    info = redis_client.info()
    print(f'Connected clients: {info.get(\"connected_clients\", \"N/A\")}')
    print(f'Used memory: {info.get(\"used_memory_human\", \"N/A\")}')
    print(f'Uptime: {info.get(\"uptime_in_seconds\", 0) // 3600} hours')
    
except Exception as e:
    print(f'Error checking queue status: {e}')
"
        ;;
    
    install-services)
        echo "Installing systemd services..."
        
        # Copy service files
        if [ -f "deploy/systemd/capitolscope-celery-worker.service" ]; then
            sudo cp deploy/systemd/capitolscope-celery-worker.service /etc/systemd/system/
            echo "Worker service file installed"
        else
            echo "ERROR: Worker service file not found"
            exit 1
        fi
        
        if [ -f "deploy/systemd/capitolscope-celery-beat.service" ]; then
            sudo cp deploy/systemd/capitolscope-celery-beat.service /etc/systemd/system/
            echo "Beat service file installed"
        else
            echo "ERROR: Beat service file not found"
            exit 1
        fi
        
        # Reload systemd
        sudo systemctl daemon-reload
        echo "Systemd services installed and reloaded"
        ;;
    
    uninstall-services)
        echo "Uninstalling systemd services..."
        
        # Stop services first
        $0 stop-all
        
        # Disable services
        sudo systemctl disable capitolscope-celery-worker || true
        sudo systemctl disable capitolscope-celery-beat || true
        
        # Remove service files
        sudo rm -f /etc/systemd/system/capitolscope-celery-worker.service
        sudo rm -f /etc/systemd/system/capitolscope-celery-beat.service
        
        # Reload systemd
        sudo systemctl daemon-reload
        echo "Systemd services uninstalled"
        ;;
    
    *)
        echo "CapitolScope Celery Management Script"
        echo ""
        echo "Usage: $0 {COMMAND}"
        echo ""
        echo "Service Management:"
        echo "  start-all           Start both worker and beat services"
        echo "  stop-all            Stop both worker and beat services"
        echo "  restart-all         Restart both worker and beat services"
        echo "  start-worker        Start worker service only"
        echo "  stop-worker         Stop worker service only"
        echo "  restart-worker      Restart worker service only"
        echo "  start-beat          Start beat service only"
        echo "  stop-beat           Stop beat service only"
        echo "  restart-beat        Restart beat service only"
        echo ""
        echo "Monitoring & Debugging:"
        echo "  status              Show service status"
        echo "  logs-worker         Follow worker logs"
        echo "  logs-beat           Follow beat logs"
        echo "  logs-all            Show recent logs from both services"
        echo "  monitor             Start Flower monitoring dashboard"
        echo "  inspect             Inspect worker status and tasks"
        echo "  queue-status        Show queue lengths and Redis status"
        echo ""
        echo "Task Management:"
        echo "  test                Test task execution"
        echo "  purge               Purge all tasks from queues (destructive!)"
        echo ""
        echo "Installation:"
        echo "  install-services    Install systemd service files"
        echo "  uninstall-services  Remove systemd service files"
        echo ""
        exit 1
        ;;
esac

exit 0



