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
def compute_scrutiny_scores(self, min_trades: int = 10, top_n: int = 50):
    """Weekly: blend alpha, conflict, cluster involvement, and disclosure lag
    into one ranked, explainable per-member Scrutiny Score."""
    _ensure_db()
    from domains.analytics.scrutiny_score import compute_scrutiny_scores as _score
    with get_sync_db_session() as session:
        scores = _score(session, min_trades=min_trades)
    for r in scores[:5]:
        logger.info("scrutiny: %s (%s) score=%.1f", r["member"], r["party"], r["scrutiny_score"])
    return {
        "status": "success",
        "members_scored": len(scores),
        "scores": scores[:top_n],
        "timestamp": datetime.utcnow().isoformat(),
    }


@celery_app.task(base=DatabaseTask, bind=True)
def backfill_earnings_events(self):
    """Weekly: refresh historical earnings dates for traded securities (feeds
    the pre-earnings proximity factor)."""
    _ensure_db()
    from domains.analytics.earnings_events import backfill_earnings_dates_sync
    with get_sync_db_session() as session:
        result = backfill_earnings_dates_sync(session)
    logger.info("backfill_earnings_events done: %s", result)
    return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(base=DatabaseTask, bind=True)
def enrich_security_sectors(self):
    """Weekly: backfill GICS sector for traded securities still missing one
    (needed by the conflict engine)."""
    _ensure_db()
    from domains.securities.sector_enrichment import enrich_missing_sectors_sync
    with get_sync_db_session() as session:
        result = enrich_missing_sectors_sync(session)
    logger.info("enrich_security_sectors done: %s", result)
    return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(base=DatabaseTask, bind=True)
def detect_committee_conflicts(self, min_conflicts: int = 3, top_n: int = 50):
    """Weekly: flag committee x sector conflicts (member trades a company in a
    sector their committee oversees) and rank members by conflicted notional."""
    _ensure_db()
    from domains.analytics.conflicts import detect_committee_conflicts as _detect
    with get_sync_db_session() as session:
        result = _detect(session, min_conflicts=min_conflicts)
    for m in result["leaderboard"][:5]:
        logger.info(
            "conflict: %s (%s) %d trades, notional=%s, sectors=%s",
            m["member"], m["party"], m["conflict_trades"],
            m["conflicted_notional"], m["top_sectors"],
        )
    result["leaderboard"] = result["leaderboard"][:top_n]
    result["status"] = "success"
    result["timestamp"] = datetime.utcnow().isoformat()
    return result


@celery_app.task(base=DatabaseTask, bind=True)
def detect_trade_clusters(self, window_days: int = 14, min_members: int = 3, top_n: int = 50):
    """Weekly: detect cluster events (N members trading the same ticker + side in
    a rolling window). Returns the ranked clusters; logs the head."""
    _ensure_db()
    from domains.analytics.clustering import detect_cluster_events
    with get_sync_db_session() as session:
        clusters = detect_cluster_events(session, window_days=window_days, min_members=min_members)

    for c in clusters[:5]:
        logger.info(
            "cluster: %d members %s %s in %dd (%s..%s) ret30=%s parties=%s lead=%s",
            c["member_count"], c["direction"], c["ticker"], c["span_days"],
            c["window_start"], c["window_end"], c["avg_return_30d"],
            c["party_breakdown"], c["lead_member"],
        )
    return {
        "status": "success",
        "clusters_found": len(clusters),
        "clusters": clusters[:top_n],
        "params": {"window_days": window_days, "min_members": min_members},
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
