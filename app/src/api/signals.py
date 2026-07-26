"""
Signals API — a machine-facing feed of congressional-trading intelligence for
consumption by external systems (Project Canary OSINT ingestion, Zeus's
reference/MCP layer, and any other client).

Design goals:
  - stable, typed JSON (every entity labelled member / ticker / sector)
  - oriented at the caller's jobs: stock selection and event-linked research
  - key-gated: every request must present a valid X-API-Key

All figures are built on public STOCK Act disclosures. Amounts are
disclosed-range midpoints. These are leads and signals, not investment advice
or accusations.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from core.config import get_settings
from core.database import get_sync_db_session
from core.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter()

# disclosed-amount midpoint, in dollars
_NOTIONAL_SQL = "COALESCE(t.amount_exact, (t.amount_min + t.amount_max) / 2.0, t.amount_min, t.amount_max, 0)"

_CACHE: Dict[str, Tuple[float, Any]] = {}
_TTL = 900  # 15 minutes


# ---------------------------------------------------------------- auth
async def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    settings = get_settings()
    configured = settings.SIGNALS_API_KEY
    if not configured:
        raise HTTPException(status_code=503, detail="Signals API not configured (no SIGNALS_API_KEY)")
    if not x_api_key or x_api_key != configured.get_secret_value():
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")


async def _cached(key: str, fn):
    now = time.time()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    data = await asyncio.to_thread(fn)
    _CACHE[key] = (now + _TTL, data)
    return data


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- helpers
def _active_tickers(days: int, limit: int):
    from sqlalchemy import text
    with get_sync_db_session() as s:
        rows = s.execute(text(
            f"""
            SELECT se.ticker,
                   MAX(sec.name) AS sector,
                   MAX(se.name) AS security_name,
                   COUNT(*) AS trades,
                   COUNT(DISTINCT t.member_id) AS members,
                   COUNT(*) FILTER (WHERE t.transaction_type = 'P') AS buys,
                   COUNT(*) FILTER (WHERE t.transaction_type = 'S') AS sells,
                   SUM({_NOTIONAL_SQL}) AS notional,
                   SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type = 'P') AS buy_notional,
                   SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type = 'S') AS sell_notional
            FROM congressional_trades t
            JOIN securities se ON se.id = t.security_id
            LEFT JOIN sectors sec ON sec.gics_code = se.sector_gics_code
            WHERE t.security_id IS NOT NULL
              AND t.transaction_type IN ('P', 'S')
              AND t.transaction_date >= (CURRENT_DATE - CAST(:days AS INTEGER))
              AND t.transaction_date <= CURRENT_DATE
            GROUP BY se.ticker
            ORDER BY members DESC, notional DESC
            LIMIT :lim
            """
        ), {"days": days, "lim": limit}).fetchall()
    out = []
    for r in rows:
        buys, sells = r[5], r[6]
        out.append({
            "type": "ticker", "ticker": r[0], "sector": r[1], "security_name": r[2],
            "trades": r[3], "members": r[4], "buys": buys, "sells": sells,
            "net_direction": "accumulating" if buys > sells else "distributing" if sells > buys else "mixed",
            "buy_sell_ratio": round(buys / sells, 2) if sells else None,
            "notional": round(float(r[7] or 0), 0),
            "buy_notional": round(float(r[8] or 0), 0),
            "sell_notional": round(float(r[9] or 0), 0),
        })
    return out


def _recent_trades(days: int, limit: int, ticker: Optional[str], party: Optional[str],
                   direction: Optional[str], min_amount: Optional[float]):
    from sqlalchemy import text
    clauses = [
        "t.transaction_date >= (CURRENT_DATE - CAST(:days AS INTEGER)) "
        "AND t.transaction_date <= CURRENT_DATE",
        "t.transaction_type IN ('P','S')",
    ]
    params: Dict[str, Any] = {"days": days, "lim": limit}
    if ticker:
        clauses.append("upper(se.ticker) = :ticker")
        params["ticker"] = ticker.upper()
    if party:
        clauses.append("m.party = :party")
        params["party"] = party.upper()
    if direction:
        clauses.append("t.transaction_type = :dir")
        params["dir"] = "P" if direction.upper().startswith("B") else "S"
    if min_amount:
        clauses.append(f"{_NOTIONAL_SQL} >= :minamt")
        params["minamt"] = min_amount
    where = " AND ".join(clauses)
    with get_sync_db_session() as s:
        rows = s.execute(text(
            f"""
            SELECT t.transaction_date, t.notification_date, m.full_name, m.party, m.chamber,
                   se.ticker, sec.name AS sector, t.transaction_type, t.owner,
                   {_NOTIONAL_SQL} AS notional, t.price_change_30d
            FROM congressional_trades t
            JOIN congress_members m ON m.id = t.member_id
            LEFT JOIN securities se ON se.id = t.security_id
            LEFT JOIN sectors sec ON sec.gics_code = se.sector_gics_code
            WHERE {where}
            ORDER BY t.transaction_date DESC, t.notification_date DESC
            LIMIT :lim
            """
        ), params).fetchall()
    out = []
    for r in rows:
        lag = (r[1] - r[0]).days if (r[1] and r[0] and r[1] >= r[0]) else None
        out.append({
            "type": "trade",
            "transaction_date": r[0].isoformat(), "disclosed_date": r[1].isoformat() if r[1] else None,
            "member": r[2], "party": r[3], "chamber": r[4],
            "ticker": r[5], "sector": r[6],
            "direction": "BUY" if r[7] == "P" else "SELL", "owner": r[8],
            "amount": round(float(r[9] or 0), 0),
            "return_30d": round(float(r[10]), 4) if r[10] is not None else None,
            "disclosure_lag_days": lag,
        })
    return out


def _sector_flow(days: int):
    from sqlalchemy import text
    with get_sync_db_session() as s:
        rows = s.execute(text(
            f"""
            SELECT sec.name AS sector,
                   COUNT(*) AS trades,
                   COUNT(DISTINCT t.member_id) AS members,
                   SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type = 'P') AS buy_notional,
                   SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type = 'S') AS sell_notional
            FROM congressional_trades t
            JOIN securities se ON se.id = t.security_id
            JOIN sectors sec ON sec.gics_code = se.sector_gics_code
            WHERE t.transaction_type IN ('P','S')
              AND t.transaction_date >= (CURRENT_DATE - CAST(:days AS INTEGER))
              AND t.transaction_date <= CURRENT_DATE
            GROUP BY sec.name
            ORDER BY (COALESCE(SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type='P'),0)
                     - COALESCE(SUM({_NOTIONAL_SQL}) FILTER (WHERE t.transaction_type='S'),0)) DESC
            """
        ), {"days": days}).fetchall()
    out = []
    for r in rows:
        buy = float(r[3] or 0)
        sell = float(r[4] or 0)
        out.append({
            "type": "sector", "sector": r[0], "trades": r[1], "members": r[2],
            "buy_notional": round(buy, 0), "sell_notional": round(sell, 0),
            "net_notional": round(buy - sell, 0),
            "flow": "inflow" if buy > sell else "outflow" if sell > buy else "flat",
        })
    return out


def _recent_clusters(days: int, limit: int):
    from domains.analytics.clustering import detect_cluster_events
    with get_sync_db_session() as s:
        clusters = detect_cluster_events(s, window_days=14, min_members=3)
    cutoff = (datetime.now(timezone.utc).date())
    fresh = [c for c in clusters if (cutoff - datetime.fromisoformat(c["window_end"]).date()).days <= days]
    return fresh[:limit]


def _most_active_members(days: int, limit: int):
    """Cheap SQL alternative to the scrutiny leaderboard for the digest: members
    by recent trade volume (the full composite score is at /leaderboard)."""
    from sqlalchemy import text
    with get_sync_db_session() as s:
        rows = s.execute(text(
            f"""
            SELECT m.full_name, m.party, COUNT(*) AS trades,
                   COUNT(DISTINCT se.ticker) AS tickers,
                   COUNT(*) FILTER (WHERE t.transaction_type='P') AS buys,
                   COUNT(*) FILTER (WHERE t.transaction_type='S') AS sells,
                   SUM({_NOTIONAL_SQL}) AS notional
            FROM congressional_trades t
            JOIN congress_members m ON m.id = t.member_id
            LEFT JOIN securities se ON se.id = t.security_id
            WHERE t.transaction_type IN ('P','S')
              AND t.transaction_date >= (CURRENT_DATE - CAST(:days AS INTEGER))
              AND t.transaction_date <= CURRENT_DATE
            GROUP BY m.full_name, m.party
            ORDER BY trades DESC, notional DESC
            LIMIT :lim
            """
        ), {"days": days, "lim": limit}).fetchall()
    return [{
        "type": "member", "member": r[0], "party": r[1], "trades": r[2],
        "tickers": r[3], "buys": r[4], "sells": r[5],
        "notional": round(float(r[6] or 0), 0),
    } for r in rows]


def _leaderboard_full():
    """Full composite Scrutiny Score leaderboard (the one heavy compute).
    Cached under a single key regardless of the caller's limit, and warmed in
    the background, so external callers never pay the cold cost."""
    from domains.analytics.scrutiny_score import compute_scrutiny_scores
    with get_sync_db_session() as s:
        scores = compute_scrutiny_scores(s, min_trades=10)
    out = []
    for r in scores:
        top = max(r["factors"].items(), key=lambda kv: kv[1]["contribution"])
        out.append({
            "type": "member", "member": r["member"], "party": r["party"], "chamber": r["chamber"],
            "scrutiny_score": r["scrutiny_score"], "trades": r["trades"],
            "leading_factor": top[0],
        })
    return out


def _build_digest(days: int):
    return {
        "active_tickers": _active_tickers(days=max(days, 30), limit=12),
        "recent_notable_trades": _recent_trades(
            days=days, limit=15, ticker=None, party=None, direction=None, min_amount=50000,
        ),
        "sector_flow": _sector_flow(days=max(days, 30)),
        "recent_clusters": _recent_clusters(days=max(days, 30), limit=8),
        "most_active_members": _most_active_members(days=max(days, 30), limit=10),
    }


async def warm_caches() -> None:
    """Pre-populate the heavy caches so external callers hit warm data.
    Best-effort; never raises."""
    try:
        await _cached("leaderboard_full", _leaderboard_full)
        await _cached("digest:7", lambda: _build_digest(7))
    except Exception as exc:  # noqa: BLE001
        logger.warning("signals cache warm failed: %s", exc)


async def cache_warmer_loop(interval: int = 600) -> None:
    """Refresh the heavy caches a little before the 15-minute TTL expires."""
    while True:
        await warm_caches()
        await asyncio.sleep(interval)


# ---------------------------------------------------------------- endpoints
@router.get("/active-tickers", dependencies=[Depends(require_api_key)])
async def active_tickers(days: int = Query(90, ge=1, le=365), limit: int = Query(50, ge=1, le=200)):
    """Tickers ranked by recent congressional activity — what Congress is
    accumulating or distributing."""
    data = await _cached(f"active:{days}:{limit}", lambda: _active_tickers(days, limit))
    return success_response(data={"generated_at": _now_iso(), "window_days": days, "tickers": data})


@router.get("/recent-trades", dependencies=[Depends(require_api_key)])
async def recent_trades(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    ticker: Optional[str] = None,
    party: Optional[str] = None,
    direction: Optional[str] = Query(None, description="buy|sell"),
    min_amount: Optional[float] = None,
):
    """Filterable recent-trade feed with sector and 30-day return context."""
    key = f"recent:{days}:{limit}:{ticker}:{party}:{direction}:{min_amount}"
    data = await _cached(key, lambda: _recent_trades(days, limit, ticker, party, direction, min_amount))
    return success_response(data={"generated_at": _now_iso(), "window_days": days, "trades": data})


@router.get("/sector-flow", dependencies=[Depends(require_api_key)])
async def sector_flow(days: int = Query(90, ge=1, le=365)):
    """Net congressional dollar flow by GICS sector — a rotation signal."""
    data = await _cached(f"sector:{days}", lambda: _sector_flow(days))
    return success_response(data={"generated_at": _now_iso(), "window_days": days, "sectors": data})


@router.get("/clusters", dependencies=[Depends(require_api_key)])
async def clusters(days: int = Query(30, ge=1, le=365), limit: int = Query(40, ge=1, le=200)):
    """Recent herding events: several members trading the same ticker + side in
    a 14-day window, notability-ranked."""
    data = await _cached(f"clusters:{days}:{limit}", lambda: _recent_clusters(days, limit))
    return success_response(data={"generated_at": _now_iso(), "window_days": days, "clusters": data})


@router.get("/leaderboard", dependencies=[Depends(require_api_key)])
async def leaderboard(limit: int = Query(50, ge=1, le=200)):
    """Compact composite Scrutiny Score leaderboard."""
    full = await _cached("leaderboard_full", _leaderboard_full)
    return success_response(data={"generated_at": _now_iso(), "members": full[:limit]})


@router.get("/digest", dependencies=[Depends(require_api_key)])
async def digest(days: int = Query(7, ge=1, le=90)):
    """One-call research brief: the freshest, highest-signal items across every
    feed — for a daily intelligence digest."""

    # Fast SQL + the moderate cluster scan, so the digest returns quickly even
    # on a cold cache (the heavy composite leaderboard is its own endpoint).
    data = await _cached(f"digest:{days}", lambda: _build_digest(days))
    return success_response(data={
        "generated_at": _now_iso(),
        "window_days": days,
        "note": "Public STOCK Act disclosures. Signals for research, not investment advice.",
        **data,
    })
