"""
Production Celery configuration for CapitolScope background tasks.

This module provides a robust, production-ready Celery configuration with:
- Multiple task queues for different workloads
- Proper error handling and logging
- Task monitoring and health checks
- Resource limits and security settings
"""

import os
import logging
from celery import Celery
from celery.signals import setup_logging, worker_ready, worker_shutdown, task_prerun, task_postrun, task_failure
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

# Import enhanced logging configuration
from background.logging_config import configure_celery_logging, get_task_logger

# Configure production logging
configure_celery_logging()
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
        'background.tasks.sync_congressional_members': {'queue': 'data_ingestion'},
        'background.tasks.comprehensive_data_ingestion': {'queue': 'data_ingestion'},
        'background.tasks.update_stock_prices': {'queue': 'price_updates'},
        'background.tasks.fetch_stock_data_enhanced': {'queue': 'price_updates'},
        'background.tasks.seed_securities_database': {'queue': 'data_ingestion'},
        'background.tasks.import_congressional_data_csvs': {'queue': 'data_ingestion'},
        'background.tasks.cleanup_old_data': {'queue': 'maintenance'},
        'background.tasks.send_trade_alerts': {'queue': 'notifications'},
        'background.tasks.generate_analytics_report': {'queue': 'maintenance'},
        'background.tasks.health_check_congress_api': {'queue': 'health_checks'},
        'background.tasks.system_health_check': {'queue': 'health_checks'},
        'background.tasks.process_pending_notifications': {'queue': 'notifications'},
        'background.tasks.daily_maintenance': {'queue': 'maintenance'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {'routing_key': 'default'},
        'notifications': {'routing_key': 'notifications'},
        'data_ingestion': {'routing_key': 'data_ingestion'},
        'price_updates': {'routing_key': 'price_updates'},
        'maintenance': {'routing_key': 'maintenance'},
        'health_checks': {'routing_key': 'health_checks'},
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
        'options': {'queue': 'health_checks', 'priority': 5}
    },
    
    # Congressional API health check - every 10 minutes
    'congress-api-health-check': {
        'task': 'background.tasks.health_check_congress_api',
        'schedule': 600.0,  # 10 minutes
        'options': {'queue': 'health_checks', 'priority': 5}
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
    
    # Daily analytics report - 4 AM UTC
    'daily-analytics-report': {
        'task': 'background.tasks.generate_analytics_report',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'maintenance', 'priority': 3}
    },
    
    # Weekly analytics report - Monday 5 AM UTC  
    'weekly-analytics-report': {
        'task': 'background.tasks.generate_analytics_report',
        'schedule': crontab(hour=5, minute=0, day_of_week=1),
        'options': {'queue': 'maintenance', 'priority': 3}
    },
}

@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery - handled by logging_config module."""
    # Logging is already configured by logging_config module
    pass

@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Log when worker is ready."""
    logger.info("Celery worker is ready and waiting for tasks")

@worker_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """Log when worker is shutting down."""
    logger.info("Celery worker is shutting down")

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when task starts."""
    task_logger = get_task_logger(task.name, task_id)
    task_logger.task_started()

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """Log when task completes successfully."""
    task_logger = get_task_logger(task.name, task_id)
    retval = kwargs.get('retval')
    task_logger.task_completed(result=retval)

@task_failure.connect
def task_failure_handler(task_id, exception, einfo, *args, **kwargs):
    """Log when task fails."""
    task_name = kwargs.get('sender', {}).name if kwargs.get('sender') else 'unknown'
    task_logger = get_task_logger(task_name, task_id)
    task_logger.task_failed(exception)

if __name__ == '__main__':
    celery_app.start()
