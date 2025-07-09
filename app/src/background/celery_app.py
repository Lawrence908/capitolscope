"""
Celery application configuration for CapitolScope background tasks.
"""

import os
from celery import Celery
from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "capitolscope",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['background.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'sync-congressional-trades': {
        'task': 'background.tasks.sync_congressional_trades',
        'schedule': 3600.0,  # Every hour
    },
    'update-stock-prices': {
        'task': 'background.tasks.update_stock_prices',
        'schedule': 900.0,  # Every 15 minutes during market hours
    },
    'cleanup-old-data': {
        'task': 'background.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Daily
    },
}

if __name__ == '__main__':
    celery_app.start() 