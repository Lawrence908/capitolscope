"""
Celery application configuration for CapitolScope background tasks.
"""

from celery import Celery
from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "capitolscope",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['background.tasks', 'background.analytics_tasks']
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
        'schedule': 86400.0,  # Daily orchestrated fetch + import
    },
    'update-stock-prices': {
        'task': 'background.tasks.update_stock_prices',
        'schedule': 900.0,  # Every 15 minutes during market hours
    },
    'cleanup-old-data': {
        'task': 'background.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Daily
    },
    'process-pending-trade-alerts': {
        'task': 'background.tasks.process_pending_trade_alerts',
        'schedule': 600.0,  # Every 10 min; batched digest, deduped via NotificationDelivery
    },
    # Analytics data-readiness refreshes (Phase 0 backfills).
    'refresh-daily-prices': {
        'task': 'background.analytics_tasks.refresh_daily_prices',
        'schedule': 86400.0,  # Daily; incremental, chains into trade returns
    },
    'refresh-member-committees': {
        'task': 'background.analytics_tasks.refresh_member_committees',
        'schedule': 604800.0,  # Weekly; roster changes rarely
    },
    'refresh-security-matching': {
        'task': 'background.analytics_tasks.refresh_security_matching',
        'schedule': 604800.0,  # Weekly; catches newly-added securities
    },
    'compute-member-analytics': {
        'task': 'background.analytics_tasks.compute_member_analytics',
        'schedule': 604800.0,  # Weekly; alpha leaderboard + disclosure-lag
    },
    'detect-trade-clusters': {
        'task': 'background.analytics_tasks.detect_trade_clusters',
        'schedule': 604800.0,  # Weekly; "N members did the same thing" events
    },
    'enrich-security-sectors': {
        'task': 'background.analytics_tasks.enrich_security_sectors',
        'schedule': 604800.0,  # Weekly; sector backfill for the conflict engine
    },
    'backfill-earnings-events': {
        'task': 'background.analytics_tasks.backfill_earnings_events',
        'schedule': 604800.0,  # Weekly; earnings dates for pre-earnings factor
    },
    'detect-committee-conflicts': {
        'task': 'background.analytics_tasks.detect_committee_conflicts',
        'schedule': 604800.0,  # Weekly; committee x sector overlap
    },
    'compute-scrutiny-scores': {
        'task': 'background.analytics_tasks.compute_scrutiny_scores',
        'schedule': 604800.0,  # Weekly; composite score across all signals
    },
}

if __name__ == '__main__':
    celery_app.start() 