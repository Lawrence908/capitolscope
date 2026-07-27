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

# Each signal engine runs several aggregate queries and takes ~10s cold; a burst
# of visitors hitting an expired key would otherwise each launch its own compute
# and contend for CPU + the sync DB pool, ballooning every one of them past the
# frontend's 30s timeout. A per-key lock collapses concurrent cold requests into
# a single compute; the _REFRESHING set does the same for background refreshes.
_LOCKS: Dict[str, asyncio.Lock] = {}
_REFRESHING: set[str] = set()


def _store(key: str, data: Any) -> None:
    _CACHE[key] = (time.time() + _TTL_SECONDS, data)


def _refresh_in_background(key: str, fn) -> None:
    """Recompute an expired key without blocking the caller (single-flight)."""
    if key in _REFRESHING:
        return
    _REFRESHING.add(key)

    async def _run():
        try:
            _store(key, await asyncio.to_thread(fn))
        except Exception:
            logger.exception("background refresh failed for analytics key %s", key)
        finally:
            _REFRESHING.discard(key)

    asyncio.create_task(_run())


async def _cached(key: str, fn) -> Any:
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]  # fresh
    if hit:
        # Stale-while-revalidate: serve the stale payload instantly and refresh
        # in the background so nobody waits on the recompute after the first warm.
        _refresh_in_background(key, fn)
        return hit[1]

    # Cold (no cached value yet): compute under a per-key lock so concurrent
    # callers share the single in-flight compute instead of stampeding.
    lock = _LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _CACHE.get(key)
        if hit and hit[0] > time.time():
            return hit[1]  # filled while we waited on the lock
        data = await asyncio.to_thread(fn)
        _store(key, data)
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


@router.get("/ticker/{ticker}", summary="Congressional trades for one ticker")
async def get_ticker_trades(ticker: str, limit: int = Query(300, ge=1, le=1000)):
    """All congressional trades for a ticker (member, party, direction, amount,
    30d return), with a summary — powers the ticker drawer."""
    sym = ticker.strip().upper()

    def compute():
        from sqlalchemy import text as _t
        with get_sync_db_session() as session:
            rows = session.execute(_t(
                """
                SELECT t.transaction_date, t.notification_date, t.transaction_type,
                       t.owner, t.amount_min, t.amount_max, t.amount_exact,
                       t.price_change_30d, m.full_name, m.party, m.id AS member_id,
                       sec.name AS sector, se.name AS security_name
                FROM congressional_trades t
                JOIN congress_members m ON m.id = t.member_id
                JOIN securities se ON se.id = t.security_id
                LEFT JOIN sectors sec ON sec.gics_code = se.sector_gics_code
                WHERE upper(se.ticker) = :sym
                ORDER BY t.transaction_date DESC
                """
            ), {"sym": sym}).fetchall()

        trades = []
        buys = sells = 0
        rets = []
        members = set()
        notional = 0.0
        sector = None
        security_name = None
        for (tdate, ndate, ttype, owner, amin, amax, aexact, ret30,
             name, party, member_id, sec_name, sec_secname) in rows:
            sector = sector or sec_name
            security_name = security_name or sec_secname
            members.add(name)
            if ttype == "P":
                buys += 1
            elif ttype == "S":
                sells += 1
            n = (float(aexact) if aexact
                 else (float(amin) + float(amax)) / 2.0 if (amin and amax)
                 else float(amin or amax) if (amin or amax) else 0.0)
            notional += n
            signed = None
            if ret30 is not None and ttype in ("P", "S"):
                signed = (1 if ttype == "P" else -1) * float(ret30)
                rets.append(signed)
            lag = (ndate - tdate).days if (ndate and tdate and ndate >= tdate) else None
            trades.append({
                "date": tdate.isoformat(),
                "member": name, "member_id": str(member_id) if member_id is not None else None,
                "party": party,
                "direction": "BUY" if ttype == "P" else "SELL" if ttype == "S" else ttype,
                "owner": owner, "amount": round(n, 0),
                "signed_return_30d": round(signed, 4) if signed is not None else None,
                "lag_days": lag,
            })

        return {
            "ticker": sym,
            "security_name": security_name,
            "sector": sector,
            "trade_count": len(trades),
            "member_count": len(members),
            "buys": buys, "sells": sells,
            "total_notional": round(notional, 0),
            "avg_return_30d": round(sum(rets) / len(rets), 4) if rets else None,
            "trades": trades,
        }

    data = await _cached(f"ticker:{sym}", compute)
    limited = {**data, "trades": data["trades"][:limit]}
    return success_response(data=limited, meta={"ticker": sym})


@router.get("/ticker/{ticker}/market", summary="Latest price + basics for one ticker")
async def get_ticker_market(ticker: str):
    """Market snapshot for a ticker, served entirely from the locally-ingested
    ``daily_prices`` history (no live external calls): latest close, day change
    vs the prior close, volume, 52-week range, ~1y of closes for a sparkline,
    plus company basics and a Yahoo Finance link.

    NOTE: prices in ``daily_prices`` are stored as whole-dollar integers, so
    values here are US dollars (whole-dollar precision), not cents.
    """
    sym = ticker.strip().upper()

    def compute():
        from sqlalchemy import text as _t
        with get_sync_db_session() as session:
            meta = session.execute(_t(
                """
                SELECT se.id, se.name AS security_name, se.currency,
                       sec.name AS sector, ex.name AS exchange
                FROM securities se
                LEFT JOIN sectors sec ON sec.gics_code = se.sector_gics_code
                LEFT JOIN exchanges ex ON ex.code = se.exchange_code
                WHERE upper(se.ticker) = :sym
                ORDER BY (SELECT count(*) FROM daily_prices dp WHERE dp.security_id = se.id) DESC
                LIMIT 1
                """
            ), {"sym": sym}).fetchone()

            history = []
            if meta is not None:
                # ~1 trading year, oldest-first, for a sparkline + 52w range.
                rows = session.execute(_t(
                    """
                    SELECT price_date, close_price
                    FROM daily_prices
                    WHERE security_id = :sid
                    ORDER BY price_date DESC
                    LIMIT 260
                    """
                ), {"sid": meta.id}).fetchall()
                history = [
                    {"date": d.isoformat(), "close": int(c)}
                    for d, c in reversed(rows) if c is not None
                ]

        yahoo_url = f"https://finance.yahoo.com/quote/{sym}"
        if meta is None or not history:
            return {
                "ticker": sym,
                "security_name": meta.security_name if meta else None,
                "sector": meta.sector if meta else None,
                "exchange": meta.exchange if meta else None,
                "currency": (meta.currency if meta else None) or "USD",
                "as_of": None,
                "last_close": None,
                "prev_close": None,
                "day_change": None,
                "day_change_pct": None,
                "week52_high": None,
                "week52_low": None,
                "history": [],
                "yahoo_url": yahoo_url,
                "has_prices": False,
            }

        last = history[-1]
        prev_close = history[-2]["close"] if len(history) >= 2 else None
        last_close = last["close"]
        day_change = (last_close - prev_close) if prev_close is not None else None
        day_change_pct = (
            round(day_change / prev_close * 100, 2)
            if (day_change is not None and prev_close) else None
        )
        closes = [h["close"] for h in history]

        return {
            "ticker": sym,
            "security_name": meta.security_name,
            "sector": meta.sector,
            "exchange": meta.exchange,
            "currency": meta.currency or "USD",
            "as_of": last["date"],
            "last_close": last_close,
            "prev_close": prev_close,
            "day_change": day_change,
            "day_change_pct": day_change_pct,
            "week52_high": max(closes),
            "week52_low": min(closes),
            "history": history,
            "yahoo_url": yahoo_url,
            "has_prices": True,
        }

    data = await _cached(f"ticker_market:{sym}", compute)
    return success_response(data=data, meta={"ticker": sym})


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


# --------------------------------------------------------------- cache warming

def _warm_scrutiny(min_trades: int = 10):
    from domains.analytics.scrutiny_score import compute_scrutiny_scores, WEIGHTS
    with get_sync_db_session() as session:
        return {"weights": WEIGHTS, "scores": compute_scrutiny_scores(session, min_trades=min_trades)}


def _warm_clusters():
    from domains.analytics.clustering import detect_cluster_events
    with get_sync_db_session() as session:
        return detect_cluster_events(session, window_days=14, min_members=3, rank_by="notability_score")


def _warm_conflicts(min_conflicts: int = 3):
    from domains.analytics.conflicts import detect_committee_conflicts
    with get_sync_db_session() as session:
        return detect_committee_conflicts(session, min_conflicts=min_conflicts)


def _warm_lag():
    from domains.analytics.returns_analytics import compute_disclosure_lag_stats
    with get_sync_db_session() as session:
        return compute_disclosure_lag_stats(session)


async def warm_caches() -> None:
    """Pre-populate the Scrutiny dashboard's heavy caches (matching the keys the
    frontend requests) so no visitor ever waits on a cold compute. Best-effort;
    never raises. Keys mirror the defaults in useScrutiny.ts."""
    warmers = {
        "scrutiny:10": _warm_scrutiny,
        "clusters:14:3:notability_score": _warm_clusters,
        "conflicts:3": _warm_conflicts,
        "disclosure_lag": _warm_lag,
    }
    for key, fn in warmers.items():
        try:
            await _cached(key, fn)
        except Exception as exc:  # noqa: BLE001
            logger.warning("analytics cache warm failed for %s: %s", key, exc)


async def cache_warmer_loop(interval: int = 1500) -> None:
    """Refresh the dashboard caches a little before the 30-minute TTL expires."""
    while True:
        await warm_caches()
        await asyncio.sleep(interval)
