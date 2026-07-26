"""
Analytics API: composite Scrutiny Score and supporting signals.

The signal engines are synchronous and moderately expensive (several
aggregate queries each), so results are computed in a threadpool and held in a
short in-process TTL cache. The weekly Celery tasks recompute the same numbers;
these endpoints simply make them queryable for the dashboard.

Everything served here is a prioritisation aid built on public STOCK Act
disclosures, not an accusation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Query

from core.database import get_sync_db_session
from core.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter()

# name -> (expires_at, payload)
_CACHE: Dict[str, Tuple[float, Any]] = {}
_TTL_SECONDS = 1800  # 30 minutes


async def _cached(key: str, fn) -> Any:
    now = time.time()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    data = await asyncio.to_thread(fn)
    _CACHE[key] = (now + _TTL_SECONDS, data)
    return data


@router.get("/scrutiny", summary="Composite Scrutiny Score leaderboard")
async def get_scrutiny_scores(
    min_trades: int = Query(10, ge=1, le=100),
    limit: int = Query(100, ge=1, le=500),
):
    """Ranked, explainable per-member Scrutiny Score (edge + conflict + cluster
    + disclosure-lag), each with a full factor breakdown."""
    def compute():
        from domains.analytics.scrutiny_score import compute_scrutiny_scores, WEIGHTS
        with get_sync_db_session() as session:
            scores = compute_scrutiny_scores(session, min_trades=min_trades)
        return {"weights": WEIGHTS, "scores": scores}

    payload = await _cached(f"scrutiny:{min_trades}", compute)
    scores = payload["scores"]
    return success_response(
        data={
            "weights": payload["weights"],
            "members_scored": len(scores),
            "scores": scores[:limit],
        },
        meta={"min_trades": min_trades, "cache_ttl_seconds": _TTL_SECONDS},
    )


@router.get("/clusters", summary="Cluster events (herding)")
async def get_clusters(
    window_days: int = Query(14, ge=1, le=90),
    min_members: int = Query(3, ge=2, le=20),
    limit: int = Query(50, ge=1, le=200),
    rank_by: str = Query("notability_score", pattern="^(notability_score|member_count)$"),
):
    """Groups of members trading the same ticker + side in a rolling window,
    ranked by base-popularity-weighted notability (or raw member count)."""
    def compute():
        from domains.analytics.clustering import detect_cluster_events
        with get_sync_db_session() as session:
            return detect_cluster_events(session, window_days=window_days, min_members=min_members, rank_by=rank_by)

    clusters = await _cached(f"clusters:{window_days}:{min_members}:{rank_by}", compute)
    return success_response(
        data={"clusters_found": len(clusters), "clusters": clusters[:limit]},
        meta={"window_days": window_days, "min_members": min_members, "rank_by": rank_by},
    )


@router.get("/conflicts", summary="Committee x sector conflicts")
async def get_conflicts(
    min_conflicts: int = Query(3, ge=1, le=50),
    limit: int = Query(50, ge=1, le=200),
):
    """Members flagged for trading a company in a sector their committee
    oversees, ranked by conflicted notional, plus notable individual conflicts."""
    def compute():
        from domains.analytics.conflicts import detect_committee_conflicts
        with get_sync_db_session() as session:
            return detect_committee_conflicts(session, min_conflicts=min_conflicts)

    result = await _cached(f"conflicts:{min_conflicts}", compute)
    return success_response(
        data={
            "total_conflict_trades": result["total_conflict_trades"],
            "members_flagged": result["members_flagged"],
            "leaderboard": result["leaderboard"][:limit],
            "top_conflicts": result["top_conflicts"],
        },
        meta={"min_conflicts": min_conflicts},
    )


@router.get("/disclosure-lag", summary="Filing timeliness vs the STOCK Act clock")
async def get_disclosure_lag():
    """Overall filing-timeliness stats against the 45-day STOCK Act limit, plus
    the worst late filers."""
    def compute():
        from domains.analytics.returns_analytics import compute_disclosure_lag_stats
        with get_sync_db_session() as session:
            return compute_disclosure_lag_stats(session)

    result = await _cached("disclosure_lag", compute)
    return success_response(data=result, meta={})
