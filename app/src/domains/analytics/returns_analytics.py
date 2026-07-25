"""
Phase 1 analytics: benchmark-adjusted returns (alpha) and disclosure-lag.

Everything here is direction-aware. A purchase is "well-timed" when the price
rises afterwards; a sale is "well-timed" when the price falls afterwards. So we
work with a *signed* return:

    signed_return =  +raw_return   for a purchase (P)
                     -raw_return   for a sale (S)

and a benchmark-adjusted **alpha** that strips out what SPY did over the same
window:

    alpha = direction * (trade_return - spy_return)

A member who consistently posts positive alpha timed the market in a way the
market alone does not explain. This is a lead for scrutiny, not a verdict.

The per-trade forward returns (``price_change_30d`` etc.) are already stored by
the WS2b backfill; here we add the benchmark leg, aggregate per member, attach
significance, and summarise filing timeliness (the 45-day STOCK Act clock).
"""

from __future__ import annotations

import bisect
import logging
import math
from statistics import mean, median, pstdev
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

STOCK_ACT_LIMIT_DAYS = 45
BENCHMARK_TICKER = "SPY"
# The forward window we headline on; the per-trade column already uses 30 days.
ALPHA_WINDOW_DAYS = 30


def _direction(txn_type: str) -> Optional[int]:
    t = (txn_type or "").upper()
    if t == "P":
        return 1
    if t == "S":
        return -1
    return None  # exchanges/other: no directional thesis


def _load_benchmark(session: Session):
    """Return (sorted_dates, adjusted_closes) for the SPY benchmark."""
    rows = session.execute(text(
        """
        SELECT dp.price_date, COALESCE(dp.adjusted_close, dp.close_price)
        FROM daily_prices dp
        JOIN securities se ON se.id = dp.security_id
        WHERE se.ticker = :t
        ORDER BY dp.price_date
        """
    ), {"t": BENCHMARK_TICKER}).fetchall()
    dates = [r[0] for r in rows]
    adj = [float(r[1]) for r in rows]
    return dates, adj


def _forward(dates: List, series: List, target) -> Optional[float]:
    i = bisect.bisect_left(dates, target)
    return series[i] if i < len(dates) else None


def _benchmark_return(dates, adj, txn_date, window_days: int) -> Optional[float]:
    base = _forward(dates, adj, txn_date)
    fwd = _forward(dates, adj, txn_date + _timedelta(window_days))
    if base and fwd and base > 0:
        return fwd / base - 1.0
    return None


def _timedelta(days: int):
    from datetime import timedelta
    return timedelta(days=days)


def _notional(amount_min, amount_max, amount_exact) -> Optional[float]:
    if amount_exact:
        return float(amount_exact)
    if amount_min and amount_max:
        return (float(amount_min) + float(amount_max)) / 2.0
    return float(amount_min or amount_max) if (amount_min or amount_max) else None


def compute_member_performance(session: Session, min_trades: int = 10) -> List[Dict[str, Any]]:
    """Per-member returns/alpha leaderboard for members with >= min_trades
    directional, 30d-priced trades. Sorted by average alpha, descending."""
    b_dates, b_adj = _load_benchmark(session)

    rows = session.execute(text(
        """
        SELECT t.member_id, m.full_name, m.party, m.chamber,
               t.transaction_type, t.transaction_date, t.price_change_30d,
               t.notification_date, t.amount_min, t.amount_max, t.amount_exact
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        WHERE t.price_change_30d IS NOT NULL
        """
    )).fetchall()

    by_member: Dict[Any, Dict[str, Any]] = {}
    for (mid, name, party, chamber, ttype, tdate, ret30,
         ndate, amin, amax, aexact) in rows:
        direction = _direction(ttype)
        if direction is None:
            continue
        signed = direction * float(ret30)
        bench = _benchmark_return(b_dates, b_adj, tdate, ALPHA_WINDOW_DAYS)
        alpha = None if bench is None else direction * (float(ret30) - bench)

        m = by_member.setdefault(mid, {
            "member_id": str(mid), "member": name, "party": party, "chamber": chamber,
            "signed": [], "alpha": [], "lag": [], "late": 0, "notional": 0.0, "trades": 0,
        })
        m["trades"] += 1
        m["signed"].append(signed)
        if alpha is not None:
            m["alpha"].append(alpha)
        if ndate and tdate:
            lag = (ndate - tdate).days
            if lag >= 0:
                m["lag"].append(lag)
                if lag > STOCK_ACT_LIMIT_DAYS:
                    m["late"] += 1
        notional = _notional(amin, amax, aexact)
        if notional:
            m["notional"] += notional

    out: List[Dict[str, Any]] = []
    for m in by_member.values():
        if m["trades"] < min_trades or not m["alpha"]:
            continue
        alphas = m["alpha"]
        n = len(alphas)
        avg_alpha = mean(alphas)
        sd = pstdev(alphas) if n > 1 else 0.0
        t_stat = (avg_alpha / (sd / math.sqrt(n))) if sd > 0 else 0.0
        hit = sum(1 for s in m["signed"] if s > 0) / len(m["signed"])
        out.append({
            "member_id": m["member_id"],
            "member": m["member"],
            "party": m["party"],
            "chamber": m["chamber"],
            "trades": m["trades"],
            "avg_return_30d": round(mean(m["signed"]), 4),
            "avg_alpha_30d": round(avg_alpha, 4),
            "t_stat": round(t_stat, 2),
            "hit_rate": round(hit, 3),
            "avg_lag_days": round(mean(m["lag"]), 1) if m["lag"] else None,
            "late_filings": m["late"],
            "late_pct": round(m["late"] / len(m["lag"]), 3) if m["lag"] else None,
            "total_notional": round(m["notional"], 0),
        })

    out.sort(key=lambda r: r["avg_alpha_30d"], reverse=True)
    return out


def compute_disclosure_lag_stats(session: Session) -> Dict[str, Any]:
    """Overall filing-timeliness picture plus the worst late filers."""
    lags = [r[0] for r in session.execute(text(
        """
        SELECT (notification_date - transaction_date) AS lag
        FROM congressional_trades
        WHERE notification_date IS NOT NULL AND transaction_date IS NOT NULL
          AND notification_date >= transaction_date
        """
    )).fetchall()]

    late_by_member = session.execute(text(
        f"""
        SELECT m.full_name, m.party, m.chamber,
               COUNT(*) FILTER (WHERE (t.notification_date - t.transaction_date) > {STOCK_ACT_LIMIT_DAYS}) AS late,
               COUNT(*) AS total,
               ROUND(AVG(t.notification_date - t.transaction_date)) AS avg_lag
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        WHERE t.notification_date IS NOT NULL AND t.transaction_date IS NOT NULL
          AND t.notification_date >= t.transaction_date
        GROUP BY m.full_name, m.party, m.chamber
        HAVING COUNT(*) FILTER (WHERE (t.notification_date - t.transaction_date) > {STOCK_ACT_LIMIT_DAYS}) > 0
        ORDER BY late DESC
        LIMIT 20
        """
    )).fetchall()

    total = len(lags)
    late = sum(1 for l in lags if l > STOCK_ACT_LIMIT_DAYS)
    return {
        "trades_with_lag": total,
        "avg_lag_days": round(mean(lags), 1) if lags else None,
        "median_lag_days": median(lags) if lags else None,
        "late_filings": late,
        "late_pct": round(late / total, 4) if total else None,
        "stock_act_limit_days": STOCK_ACT_LIMIT_DAYS,
        "worst_late_filers": [
            {"member": r[0], "party": r[1], "chamber": r[2],
             "late": r[3], "total": r[4], "avg_lag_days": int(r[5])}
            for r in late_by_member
        ],
    }
