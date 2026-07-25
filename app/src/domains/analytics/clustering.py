"""
Phase 2 (quick win): cluster-event detection.

A cluster event is the unit of "how many members did the same thing": several
members trading the *same ticker* in the *same direction* inside a short rolling
window. It is what turns thousands of individual disclosures into a feed of
"N members bought AAPL in the last 14 days".

Detection (per ticker + direction): walk trades in date order and group those
that fall within ``window_days`` of the group's first trade. A group with at
least ``min_members`` distinct members is emitted as a cluster event. Each
cluster is enriched with:

  - member / trade counts and the member list
  - party breakdown (coincidence vs a shared channel)
  - aggregate notional (from the disclosed amount ranges)
  - the lead member and timeline (who moved first)
  - average direction-aware 30d return of the cluster's trades, i.e. whether
    the herd was actually well-timed (uses the Phase 0/1 return data)

Needs no enrichment to run at the baseline; the return column just makes it
sharper. Results are leads for scrutiny, not verdicts.
"""

from __future__ import annotations

import logging
from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_DIRECTION = {"P": "BUY", "S": "SELL"}


def _notional(amin, amax, aexact) -> Optional[float]:
    if aexact:
        return float(aexact)
    if amin and amax:
        return (float(amin) + float(amax)) / 2.0
    return float(amin or amax) if (amin or amax) else None


def _finalise(rows: List[dict], window_days: int, min_members: int) -> Optional[Dict[str, Any]]:
    members = {r["member_id"]: r["member"] for r in rows}
    if len(members) < min_members:
        return None

    dates = [r["date"] for r in rows]
    rows_sorted = sorted(rows, key=lambda r: r["date"])
    lead = rows_sorted[0]

    notionals = [n for n in (_notional(r["amin"], r["amax"], r["aexact"]) for r in rows) if n]
    signed_returns = [
        (1 if r["direction"] == "BUY" else -1) * float(r["ret30"])
        for r in rows if r["ret30"] is not None
    ]
    parties = Counter(r["party"] for r in rows if r["party"])

    return {
        "ticker": rows[0]["ticker"],
        "direction": rows[0]["direction"],
        "window_start": min(dates).isoformat(),
        "window_end": max(dates).isoformat(),
        "span_days": (max(dates) - min(dates)).days,
        "member_count": len(members),
        "trade_count": len(rows),
        "members": sorted(set(members.values())),
        "party_breakdown": dict(parties),
        "total_notional": round(sum(notionals), 0) if notionals else None,
        "avg_return_30d": round(mean(signed_returns), 4) if signed_returns else None,
        "lead_member": lead["member"],
        "lead_date": lead["date"].isoformat(),
        "window_days": window_days,
    }


def detect_cluster_events(
    session: Session,
    window_days: int = 14,
    min_members: int = 3,
) -> List[Dict[str, Any]]:
    """Return cluster events, ranked by member_count then notional (desc)."""
    rows = session.execute(text(
        """
        SELECT t.ticker, t.transaction_type, t.transaction_date,
               t.member_id, m.full_name, m.party,
               t.amount_min, t.amount_max, t.amount_exact, t.price_change_30d
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        WHERE t.ticker IS NOT NULL AND t.ticker <> ''
          AND t.transaction_type IN ('P', 'S')
        ORDER BY t.ticker, t.transaction_type, t.transaction_date
        """
    )).fetchall()

    clusters: List[Dict[str, Any]] = []
    group_key = None
    current: List[dict] = []
    anchor = None

    def flush():
        if current:
            c = _finalise(current, window_days, min_members)
            if c:
                clusters.append(c)

    for (ticker, ttype, tdate, mid, name, party, amin, amax, aexact, ret30) in rows:
        key = (ticker, ttype)
        rec = {
            "ticker": ticker, "direction": _DIRECTION[ttype], "date": tdate,
            "member_id": mid, "member": name, "party": party,
            "amin": amin, "amax": amax, "aexact": aexact, "ret30": ret30,
        }
        if key != group_key:
            flush()
            group_key, current, anchor = key, [rec], tdate
            continue
        if (tdate - anchor).days <= window_days:
            current.append(rec)
        else:
            flush()
            current, anchor = [rec], tdate
    flush()

    clusters.sort(key=lambda c: (c["member_count"], c["total_notional"] or 0), reverse=True)
    return clusters
