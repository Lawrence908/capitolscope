"""
Celery tasks for the public X account (see domains/social/service.py).

draft_social_posts runs after every successful congressional sync (and on a
beat fallback); publish_social_posts runs every 15 minutes and posts at most
one queued post per run. Both are no-ops for writing to X unless
SOCIAL_X_ENABLED=1.
"""

from __future__ import annotations

import logging

from background.celery_app import celery_app
from background.tasks import DatabaseTask, run_async_task
from core.database import db_manager, get_sync_db_session

logger = logging.getLogger(__name__)


def _ensure_db():
    if not db_manager._initialized:
        run_async_task(db_manager.initialize())


@celery_app.task(base=DatabaseTask, bind=True)
def draft_social_posts(self):
    _ensure_db()
    from domains.social.service import draft_posts

    with get_sync_db_session() as session:
        result = draft_posts(session)
    logger.info("draft_social_posts: %s", result)
    return {"status": "success", **result}


@celery_app.task(base=DatabaseTask, bind=True)
def publish_social_posts(self):
    _ensure_db()
    from domains.social.service import publish_next

    with get_sync_db_session() as session:
        result = publish_next(session)
    if result.get("status") not in ("disabled", "outside_window", "queue_empty", "min_gap"):
        logger.info("publish_social_posts: %s", result)
    return result
