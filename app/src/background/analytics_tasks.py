"""
Scheduled analytics data-readiness tasks (Phase 0 backfills as Celery jobs).

These keep the columns the signal engines depend on fresh:

  - member committees        (weekly; the roster changes rarely)
  - trade -> security_id      (weekly; catches symbols added to the universe)
  - daily prices              (daily; incremental, only recent bars)
  - trade forward returns     (daily; chained after prices, only recent/missing)

Each wraps an idempotent backfill from ``domains.analytics`` / committee
enrichment and follows the existing sync-task pattern (DatabaseTask +
get_sync_db_session). The price task chains into the returns task so returns are
always computed against fresh prices.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from background.celery_app import celery_app
from background.tasks import DatabaseTask, run_async_task
from core.database import db_manager, get_sync_db_session

logger = logging.getLogger(__name__)


def _ensure_db():
    if not db_manager._initialized:
        run_async_task(db_manager.initialize())


@celery_app.task(base=DatabaseTask, bind=True)
def refresh_member_committees(self):
    """Weekly: backfill CongressMember.committees from congress-legislators."""
    _ensure_db()
    from domains.congressional.committee_enrichment import enrich_committees_sync
    with get_sync_db_session() as session:
        result = enrich_committees_sync(session)
    logger.info("refresh_member_committees done: %s", result)
    return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(base=DatabaseTask, bind=True)
def refresh_security_matching(self):
    """Weekly: re-resolve security_id for trades against the current universe."""
    _ensure_db()
    from domains.analytics.backfill_securities import backfill_security_matching_sync
    with get_sync_db_session() as session:
        result = backfill_security_matching_sync(session)
    logger.info("refresh_security_matching done: %s", result)
    return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(base=DatabaseTask, bind=True)
def refresh_trade_returns(self, recent_days: int = 45):
    """Daily (chained after prices): fill price_at_trade + forward returns for
    recent or still-incomplete trades."""
    _ensure_db()
    from domains.analytics.backfill_trade_returns import backfill_trade_returns_sync
    with get_sync_db_session() as session:
        result = backfill_trade_returns_sync(session, recent_days=recent_days)
    logger.info("refresh_trade_returns done: %s", result)
    return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(base=DatabaseTask, bind=True)
def compute_member_analytics(self, min_trades: int = 10, top_n: int = 25):
    """Weekly: compute the benchmark-adjusted alpha leaderboard and the
    disclosure-lag summary. Returns the ranked results (also stored in the
    Celery result backend); logs the head of each list."""
    _ensure_db()
    from domains.analytics.returns_analytics import (
        compute_member_performance,
        compute_disclosure_lag_stats,
    )
    with get_sync_db_session() as session:
        performance = compute_member_performance(session, min_trades=min_trades)
        lag = compute_disclosure_lag_stats(session)

    for r in performance[:5]:
        logger.info(
            "alpha leaderboard: %s (%s) n=%d alpha30=%.1f%% t=%.2f hit=%.2f late_pct=%s",
            r["member"], r["party"], r["trades"], r["avg_alpha_30d"] * 100,
            r["t_stat"], r["hit_rate"], r["late_pct"],
        )
    logger.info(
        "disclosure lag: avg=%sd median=%sd late=%d (%.1f%%)",
        lag["avg_lag_days"], lag["median_lag_days"], lag["late_filings"],
        (lag["late_pct"] or 0) * 100,
    )
    return {
        "status": "success",
        "member_performance": performance[:top_n],
        "members_ranked": len(performance),
        "disclosure_lag": lag,
        "timestamp": datetime.utcnow().isoformat(),
    }


@celery_app.task(base=DatabaseTask, bind=True)
def refresh_daily_prices(self, lookback_days: int = 10):
    """Daily: pull recent daily bars for tracked securities (existing dates are
    skipped), then chain into the returns refresh."""
    _ensure_db()
    from domains.analytics.backfill_prices import backfill_prices_sync
    start = (datetime.utcnow().date() - timedelta(days=lookback_days)).isoformat()
    with get_sync_db_session() as session:
        result = backfill_prices_sync(session, start=start)
    logger.info("refresh_daily_prices done (start=%s): %s", start, result)

    # Chain: recompute returns now that fresh prices have landed.
    refresh_trade_returns.delay(recent_days=45)
    return {"status": "success", "start": start, "result": result, "timestamp": datetime.utcnow().isoformat()}
