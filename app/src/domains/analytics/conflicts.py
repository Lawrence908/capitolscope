"""
Conflict-of-interest engine: committee x sector overlap.

Flags trades where a member sits on a committee whose jurisdiction covers the
sector of the company they traded. A member on Armed Services trading a defense
name (Industrials), or on Financial Services trading a bank (Financials), has a
potential conflict worth scrutiny.

Two inputs, both now populated:
  - member committees          (committee_enrichment; 524 members)
  - security GICS sector        (sector_enrichment + prior data)

``COMMITTEE_SECTOR_MAP`` is a curated, editable mapping from a committee-name
keyword to the GICS sectors it oversees. Keyword matching makes it robust to
House/Senate naming variants (e.g. both "House Committee on Armed Services" and
"Senate Committee on Armed Services" match "armed services"). Overly-broad
committees (e.g. Appropriations, Oversight) are intentionally omitted so the
signal stays specific.

Everything is a lead for scrutiny, not a verdict.
"""

from __future__ import annotations

import logging
from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# committee-name keyword -> GICS sectors under its jurisdiction
COMMITTEE_SECTOR_MAP: Dict[str, Set[str]] = {
    "armed services": {"Industrials", "Technology"},
    "energy and commerce": {"Energy", "Health Care", "Communication Services", "Utilities"},
    "energy and natural resources": {"Energy", "Utilities", "Materials"},
    "natural resources": {"Energy", "Materials", "Utilities"},
    "financial services": {"Financials", "Real Estate"},
    "banking": {"Financials", "Real Estate"},
    "finance": {"Health Care", "Financials"},           # Senate Finance
    "ways and means": {"Health Care", "Financials"},
    "taxation": {"Financials"},
    "agriculture": {"Consumer Staples", "Materials"},
    "science, space": {"Technology", "Communication Services"},
    "commerce, science": {"Communication Services", "Technology", "Industrials", "Consumer Discretionary"},
    "homeland security": {"Industrials", "Technology"},
    "intelligence": {"Technology", "Industrials"},
    "health, education": {"Health Care"},
    "veterans": {"Health Care"},
    "environment and public works": {"Utilities", "Energy", "Materials", "Industrials"},
    "transportation": {"Industrials"},
}


def jurisdiction_sectors(committees: Optional[List[str]]) -> Set[str]:
    """Union of GICS sectors overseen by a member's committees."""
    sectors: Set[str] = set()
    if not committees:
        return sectors
    for committee in committees:
        name = (committee or "").lower()
        for keyword, secs in COMMITTEE_SECTOR_MAP.items():
            if keyword in name:
                sectors |= secs
    return sectors


def detect_committee_conflicts(session: Session, min_conflicts: int = 3) -> Dict[str, Any]:
    """Flag committee x sector conflicts per trade and aggregate per member.

    Returns overall counts, a per-member leaderboard (members with at least
    ``min_conflicts`` conflicted trades, ranked by conflicted notional), and a
    sample of the most notable individual conflicts.
    """
    rows = session.execute(text(
        """
        SELECT t.member_id, m.full_name, m.party, m.committees,
               t.ticker, sec.name AS sector, t.transaction_type, t.transaction_date,
               t.amount_min, t.amount_max, t.amount_exact, t.price_change_30d
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        JOIN securities se ON se.id = t.security_id
        JOIN sectors sec ON sec.gics_code = se.sector_gics_code
        WHERE m.committees IS NOT NULL AND t.transaction_type IN ('P', 'S')
        """
    )).fetchall()

    per_member: Dict[Any, Dict[str, Any]] = {}
    total_conflicts = 0
    samples: List[Dict[str, Any]] = []

    for (mid, name, party, committees, ticker, sector, ttype, tdate,
         amin, amax, aexact, ret30) in rows:
        juris = jurisdiction_sectors(committees)
        if sector not in juris:
            continue
        total_conflicts += 1

        notional = (
            float(aexact) if aexact
            else (float(amin) + float(amax)) / 2.0 if (amin and amax)
            else float(amin or amax) if (amin or amax) else 0.0
        )
        signed_ret = (1 if ttype == "P" else -1) * float(ret30) if ret30 is not None else None

        m = per_member.setdefault(mid, {
            "member": name, "party": party, "conflicts": 0,
            "notional": 0.0, "sectors": Counter(), "committees": committees,
            "returns": [],
        })
        m["conflicts"] += 1
        m["notional"] += notional
        m["sectors"][sector] += 1
        if signed_ret is not None:
            m["returns"].append(signed_ret)

        # keep the highest-notional conflicts as illustrative samples
        which_committees = [
            c for c in committees if jurisdiction_sectors([c]) & {sector}
        ]
        samples.append({
            "member": name, "party": party, "ticker": ticker, "sector": sector,
            "direction": "BUY" if ttype == "P" else "SELL",
            "date": tdate.isoformat(), "notional": round(notional, 0),
            "committee": which_committees[0] if which_committees else None,
            "signed_return_30d": round(signed_ret, 4) if signed_ret is not None else None,
        })

    leaderboard = []
    for m in per_member.values():
        if m["conflicts"] < min_conflicts:
            continue
        leaderboard.append({
            "member": m["member"],
            "party": m["party"],
            "conflict_trades": m["conflicts"],
            "conflicted_notional": round(m["notional"], 0),
            "top_sectors": [s for s, _ in m["sectors"].most_common(3)],
            "avg_return_30d": round(mean(m["returns"]), 4) if m["returns"] else None,
        })
    leaderboard.sort(key=lambda r: r["conflicted_notional"], reverse=True)

    samples.sort(key=lambda s: s["notional"], reverse=True)
    return {
        "total_conflict_trades": total_conflicts,
        "members_flagged": len(leaderboard),
        "leaderboard": leaderboard,
        "top_conflicts": samples[:25],
    }
