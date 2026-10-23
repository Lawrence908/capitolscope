"""
Anonymous, read-only feed for the public homepage and the late-filers page.

Everything here is public record (House Clerk and Senate eFD periodic
transaction reports), so no auth: the endpoints are cheap, cached aggregates
over ``congressional_trades`` shared through ``core.analytics_cache``.

Data rules applied throughout:
  - future-dated transactions (transaction_date > today) are excluded; they are
    parse errors, not trades;
  - amended filings (filing_status = 'A') never count as "late": an amendment
    restates an earlier report, so its notification date is not the original
    disclosure date;
  - amounts are returned in CENTS exactly as stored (members report ranges).

Copy built here (notable-filing headlines) is deliberately plain and factual:
who, what, the reported range, and the dates. It never implies motive.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Sequence

from fastapi import APIRouter, Query

from core.analytics_cache import cached as _shared_cached
from core.database import get_sync_db_session
from core.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Short TTL: the homepage should pick up the daily import within minutes.
_TTL = 10 * 60
_NAMESPACE = "public"

DISCLOSURE_LIMIT_DAYS = 45
NOTABLE_WINDOW_DAYS = 90
LATEST_WINDOW_DAYS = 14
ACTIVE_WINDOW_DAYS = 60

# Shared column list for every trade row this module returns. Order matters:
# ``_trade_from_row`` maps by position.
_TRADE_COLUMNS = """
    t.id, t.member_id, m.full_name, m.party, m.state, m.chamber, m.district,
    COALESCE(se.ticker, t.ticker) AS ticker,
    COALESCE(se.name, t.asset_name, t.raw_asset_description) AS asset_name,
    t.asset_type, t.transaction_type, t.transaction_date, t.notification_date,
    t.amount_min, t.amount_max, t.amount_exact, t.filing_status, t.owner
"""
_TRADE_FROM = """
    FROM congressional_trades t
    JOIN congress_members m ON m.id = t.member_id
    LEFT JOIN securities se ON se.id = t.security_id
"""
# Not future-dated (parse errors) and not before the trade (bad dates).
_VALID = "t.transaction_date <= CURRENT_DATE"
_NOT_AMENDED = "COALESCE(t.filing_status, 'N') <> 'A'"
_LAG = "(t.notification_date - t.transaction_date)"


async def _cached(key: str, fn):
    return await _shared_cached(key, fn, ttl=_TTL, namespace=_NAMESPACE)


def _iso(d: Any) -> Optional[str]:
    return d.isoformat() if d is not None else None


# ====================================================================== pure helpers
def lag_days(transaction_date: Optional[date], notification_date: Optional[date]) -> Optional[int]:
    """Days from trade to disclosure; None when either date is missing or the
    disclosure predates the trade (a data error)."""
    if transaction_date is None or notification_date is None:
        return None
    d = (notification_date - transaction_date).days
    return d if d >= 0 else None


def is_late(lag: Optional[int], filing_status: Optional[str]) -> bool:
    """Past the 45-day limit, and not an amendment."""
    if lag is None or lag <= DISCLOSURE_LIMIT_DAYS:
        return False
    return (filing_status or "N").upper() != "A"


def short_money(cents: Optional[int]) -> str:
    """Compact dollar label from cents: 50000100 -> "$500K", 100000000 -> "$1M"."""
    if cents is None:
        return ""
    dollars = cents / 100
    if dollars >= 1_000_000:
        v = round(dollars / 1_000_000, 1)
        return f"${v:g}M"
    if dollars >= 1_000:
        return f"${round(dollars / 1_000):,}K"
    return f"${round(dollars):,}"


def bracket_phrase(amount_min: Optional[int], amount_max: Optional[int]) -> str:
    """Reported range as prose: "the $500K to $1M range"."""
    if amount_min is not None and amount_max is not None and amount_max != amount_min:
        return f"the {short_money(amount_min)} to {short_money(amount_max)} range"
    if amount_min is not None and amount_max is None:
        return f"the range above {short_money(amount_min)}"
    value = amount_min if amount_min is not None else amount_max
    if value is not None:
        return f"an amount of {short_money(value)}"
    return "an undisclosed amount"


_VERBS = {"P": ("buys", "purchase"), "S": ("sells", "sale"), "E": ("exchanges", "exchange")}


def trade_verb(transaction_type: Optional[str], noun: bool = False) -> str:
    present, as_noun = _VERBS.get((transaction_type or "").strip().upper()[:1], ("reports", "trade"))
    return as_noun if noun else present


def asset_label(ticker: Optional[str], asset_name: Optional[str], max_len: int = 36) -> str:
    """Ticker when known, otherwise a shortened asset name."""
    t = (ticker or "").strip()
    if t:
        return t
    name = re.sub(r"\s+", " ", (asset_name or "").strip())
    # "Greenbrier Affiliates : Greenbrier Fund LP" -> "Greenbrier Affiliates"
    name = re.split(r"\s+[:|]\s+", name, maxsplit=1)[0].strip()
    if not name:
        return "an undisclosed asset"
    return name if len(name) <= max_len else name[: max_len - 3].rstrip(" ,.-") + "..."


def surname(full_name: Optional[str]) -> str:
    """Last word of the name, ignoring generational suffixes."""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    while len(parts) > 1 and parts[-1].rstrip(".,").upper() in {"JR", "SR", "II", "III", "IV"}:
        parts.pop()
    return parts[-1].rstrip(",") if parts else "A member"


_COMMITTEE_PREFIX = re.compile(r"^(house|senate|joint)\s+(select\s+|permanent\s+select\s+|special\s+)?committee\s+on\s+(the\s+)?", re.I)


def committee_short(name: str) -> str:
    """"House Committee on Armed Services" -> "Armed Services"."""
    return _COMMITTEE_PREFIX.sub("", (name or "").strip()) or (name or "").strip()


def matched_committee(committees: Optional[Sequence[str]], sector: Optional[str]) -> Optional[str]:
    """The first of a member's committees whose jurisdiction (per the curated
    COMMITTEE_SECTOR_MAP) covers ``sector``; None when there is no overlap."""
    if not committees or not sector:
        return None
    from domains.analytics.conflicts import COMMITTEE_SECTOR_MAP

    for committee in committees:
        low = (committee or "").lower()
        for keyword, sectors in COMMITTEE_SECTOR_MAP.items():
            if keyword in low and sector in sectors:
                return committee
    return None


def headline_late(trade: Dict[str, Any]) -> str:
    """"Tuberville discloses May 2024 INTC purchase, 775 days past the deadline"."""
    lag = trade.get("days_to_disclose") or 0
    over = max(0, lag - DISCLOSURE_LIMIT_DAYS)
    when = ""
    td = trade.get("transaction_date")
    if td:
        d = date.fromisoformat(td[:10])
        when = f"{d.strftime('%b')} {d.year} "
    return (
        f"{surname(trade.get('member_name'))} discloses {when}"
        f"{asset_label(trade.get('ticker'), trade.get('asset_name'))} "
        f"{trade_verb(trade.get('transaction_type'), noun=True)}, "
        f"{over} day{'s' if over != 1 else ''} past the deadline"
    )


def headline_bracket(trade: Dict[str, Any]) -> str:
    """"Biggs buys BNS in the $500K to $1M range"."""
    return (
        f"{surname(trade.get('member_name'))} {trade_verb(trade.get('transaction_type'))} "
        f"{asset_label(trade.get('ticker'), trade.get('asset_name'))} in "
        f"{bracket_phrase(trade.get('amount_min'), trade.get('amount_max'))}"
    )


def headline_committee(trade: Dict[str, Any], committee: str, sector: Optional[str]) -> str:
    """"Cisneros buys MOG.A, an Industrials company, while on the Armed Services Committee"."""
    if sector:
        article = "an" if sector[:1].upper() in "AEIOU" else "a"
        what = f", {article} {sector} company,"
    else:
        what = ""
    return (
        f"{surname(trade.get('member_name'))} {trade_verb(trade.get('transaction_type'))} "
        f"{asset_label(trade.get('ticker'), trade.get('asset_name'))}{what} "
        f"while on the {committee_short(committee)} Committee"
    )


def pick_notable(
    late: Iterable[Dict[str, Any]],
    brackets: Iterable[Dict[str, Any]],
    committee: Iterable[Dict[str, Any]],
    n: int = 4,
) -> List[Dict[str, Any]]:
    """Choose up to ``n`` notable cards: the latest-filed worst lag, one
    committee overlap (if any), and the largest brackets filling the rest.
    Each card is a different trade and, where possible, a different member.

    ``committee`` items carry ``_committee`` and ``_sector`` keys.
    Returns cards ordered late, brackets..., committee.
    """
    used_trades: set = set()
    used_members: set = set()

    def take(pool: Iterable[Dict[str, Any]], distinct_member: bool = True) -> Optional[Dict[str, Any]]:
        for t in pool:
            if t["id"] in used_trades:
                continue
            if distinct_member and t.get("member_id") in used_members:
                continue
            used_trades.add(t["id"])
            used_members.add(t.get("member_id"))
            return t
        return None

    late = list(late)
    brackets = list(brackets)
    committee = list(committee)

    late_card = take(late)
    committee_card = take(committee)

    bracket_cards: List[Dict[str, Any]] = []
    slots = n - (1 if late_card else 0) - (1 if committee_card else 0)
    for _ in range(max(0, slots)):
        t = take(brackets) or take(brackets, distinct_member=False)
        if t is None:
            break
        bracket_cards.append(t)

    cards: List[Dict[str, Any]] = []
    if late_card:
        cards.append({"kind": "late", "label": "Late filing", "headline": headline_late(late_card), "trade": _public(late_card)})
    for t in bracket_cards:
        cards.append({"kind": "bracket", "label": "Top bracket", "headline": headline_bracket(t), "trade": _public(t)})
    if committee_card:
        cards.append({
            "kind": "committee",
            "label": "Committee overlap",
            "headline": headline_committee(committee_card, committee_card["_committee"], committee_card.get("_sector")),
            "committee": committee_card["_committee"],
            "sector": committee_card.get("_sector"),
            "trade": _public(committee_card),
        })
    return cards[:n]


def group_late_filers(
    trades: Iterable[Dict[str, Any]],
    filings_by_member: Optional[Dict[str, int]] = None,
    per_member: int = 50,
) -> List[Dict[str, Any]]:
    """Group late trades by member: count, worst and median lag, latest late
    filing, and the trades themselves (worst lag first, capped at
    ``per_member``). Amendments and on-time rows are dropped defensively.
    Members are ranked by late count, then worst lag."""
    groups: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        lag = t.get("days_to_disclose")
        if not is_late(lag, t.get("filing_status")):
            continue
        mid = str(t.get("member_id"))
        g = groups.get(mid)
        if g is None:
            g = groups[mid] = {
                "member_id": mid,
                "member_name": t.get("member_name"),
                "member_party": t.get("member_party"),
                "member_state": t.get("member_state"),
                "member_chamber": t.get("member_chamber"),
                "member_district": t.get("member_district"),
                "_lags": [],
                "_trades": [],
                "latest_late_filing": None,
            }
        g["_lags"].append(lag)
        g["_trades"].append(t)
        nd = t.get("notification_date")
        if nd and (g["latest_late_filing"] is None or nd > g["latest_late_filing"]):
            g["latest_late_filing"] = nd

    out = []
    for g in groups.values():
        lags = g.pop("_lags")
        rows = sorted(g.pop("_trades"), key=lambda r: (-(r.get("days_to_disclose") or 0), r.get("notification_date") or ""))
        g["late_count"] = len(lags)
        g["worst_days"] = max(lags)
        g["median_days"] = int(round(median(lags)))
        g["filings_in_window"] = (filings_by_member or {}).get(g["member_id"])
        g["trades"] = [_public(r) for r in rows[:per_member]]
        out.append(g)
    out.sort(key=lambda g: (-g["late_count"], -g["worst_days"], g["member_name"] or ""))
    return out


def _public(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Strip private (underscore) keys before a trade leaves the module."""
    return {k: v for k, v in trade.items() if not k.startswith("_")}


def _trade_from_row(r: Sequence[Any]) -> Dict[str, Any]:
    tdate, ndate = r[11], r[12]
    return {
        "id": str(r[0]),
        "member_id": str(r[1]),
        "member_name": r[2],
        "member_party": r[3],
        "member_state": r[4],
        "member_chamber": r[5],
        "member_district": r[6],
        "ticker": (r[7] or None),
        "asset_name": r[8],
        "asset_type": r[9],
        "transaction_type": r[10],
        "transaction_date": _iso(tdate),
        "notification_date": _iso(ndate),
        "amount_min": r[13],
        "amount_max": r[14],
        "amount_exact": r[15],
        "filing_status": r[16],
        "owner": r[17],
        "days_to_disclose": lag_days(tdate, ndate),
    }


# ====================================================================== SQL
def _latest_disclosures(s, limit: int = 120) -> List[Dict[str, Any]]:
    """Newest filings first. The window is anchored on the most recent filing
    (not just today) so a stalled import still shows the last two weeks."""
    from sqlalchemy import text

    rows = s.execute(text(
        f"""
        SELECT {_TRADE_COLUMNS}
        {_TRADE_FROM}
        WHERE {_VALID}
          AND t.notification_date >= (
                LEAST(CURRENT_DATE, (SELECT MAX(x.notification_date) FROM congressional_trades x
                                     WHERE x.transaction_date <= CURRENT_DATE))
                - CAST(:days AS INTEGER))
        ORDER BY t.notification_date DESC, t.transaction_date DESC, m.full_name, t.id
        LIMIT :lim
        """
    ), {"days": LATEST_WINDOW_DAYS, "lim": limit}).fetchall()
    return [_trade_from_row(r) for r in rows]


def _headline_stats(s) -> Dict[str, Any]:
    from sqlalchemy import text

    r = s.execute(text(
        f"""
        SELECT
          COUNT(*) FILTER (WHERE t.notification_date > CURRENT_DATE - 7)                         AS week_trades,
          COUNT(DISTINCT t.member_id) FILTER (WHERE t.notification_date > CURRENT_DATE - 7)      AS week_members,
          COUNT(*) FILTER (WHERE t.notification_date > CURRENT_DATE - 30)                        AS month_trades,
          COUNT(DISTINCT t.member_id) FILTER (WHERE t.notification_date > CURRENT_DATE - 30)     AS month_members,
          SUM(COALESCE(t.amount_min, t.amount_exact, t.amount_max))
              FILTER (WHERE t.notification_date > CURRENT_DATE - 30)                             AS month_min,
          SUM(COALESCE(t.amount_max, t.amount_exact, t.amount_min))
              FILTER (WHERE t.notification_date > CURRENT_DATE - 30)                             AS month_max,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY {_LAG})
              FILTER (WHERE t.notification_date > CURRENT_DATE - 30 AND {_LAG} >= 0)             AS month_median_lag,
          COUNT(*) FILTER (WHERE t.notification_date >= date_trunc('year', CURRENT_DATE)
                             AND {_LAG} > :limit AND {_NOT_AMENDED})                             AS late_ytd,
          COUNT(DISTINCT t.member_id) FILTER (WHERE t.notification_date >= date_trunc('year', CURRENT_DATE)
                             AND {_LAG} > :limit AND {_NOT_AMENDED})                             AS late_ytd_members,
          MAX(t.notification_date)                                                               AS last_filing
        FROM congressional_trades t
        WHERE {_VALID}
          AND t.notification_date >= LEAST(date_trunc('year', CURRENT_DATE)::date, CURRENT_DATE - 30)
        """
    ), {"limit": DISCLOSURE_LIMIT_DAYS}).fetchone()
    today = datetime.now(timezone.utc).date()
    return {
        "week_trades": int(r[0] or 0),
        "week_members": int(r[1] or 0),
        "month_trades": int(r[2] or 0),
        "month_members": int(r[3] or 0),
        "month_amount_min": int(r[4]) if r[4] is not None else None,
        "month_amount_max": int(r[5]) if r[5] is not None else None,
        "median_days_to_disclose_30d": int(round(float(r[6]))) if r[6] is not None else None,
        "late_this_year": int(r[7] or 0),
        "late_this_year_members": int(r[8] or 0),
        "year": today.year,
        "last_filing_date": _iso(r[9]),
    }


def _notable(s) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    window = f"{_VALID} AND t.notification_date >= CURRENT_DATE - CAST(:days AS INTEGER)"
    params = {"days": NOTABLE_WINDOW_DAYS, "limit": DISCLOSURE_LIMIT_DAYS}

    late = s.execute(text(
        f"""
        SELECT {_TRADE_COLUMNS} {_TRADE_FROM}
        WHERE {window} AND {_LAG} > :limit AND {_NOT_AMENDED}
        ORDER BY {_LAG} DESC, t.notification_date DESC
        LIMIT 20
        """
    ), params).fetchall()

    brackets = s.execute(text(
        f"""
        SELECT {_TRADE_COLUMNS} {_TRADE_FROM}
        WHERE {window} AND COALESCE(t.amount_max, t.amount_exact, t.amount_min) IS NOT NULL
        ORDER BY COALESCE(t.amount_max, t.amount_exact, t.amount_min) DESC,
                 COALESCE(t.amount_min, 0) DESC, t.notification_date DESC
        LIMIT 40
        """
    ), params).fetchall()

    overlap_rows = s.execute(text(
        f"""
        SELECT {_TRADE_COLUMNS}, m.committees, sec.name AS sector
        {_TRADE_FROM}
        JOIN sectors sec ON sec.gics_code = se.sector_gics_code
        WHERE {window}
          AND t.transaction_type IN ('P', 'S')
          AND m.committees IS NOT NULL
        ORDER BY COALESCE(t.amount_max, t.amount_exact, t.amount_min, 0) DESC, t.notification_date DESC
        LIMIT 2000
        """
    ), params).fetchall()

    committee: List[Dict[str, Any]] = []
    for r in overlap_rows:
        c = matched_committee(r[18], r[19])
        if c:
            t = _trade_from_row(r)
            t["_committee"] = committee_short(c)
            t["_sector"] = r[19]
            committee.append(t)

    return pick_notable(
        [_trade_from_row(r) for r in late],
        [_trade_from_row(r) for r in brackets],
        committee,
    )


def _most_active(s, limit: int = 8) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    rows = s.execute(text(
        f"""
        SELECT m.id, m.full_name, m.party, m.state, m.chamber, m.district,
               COUNT(*) AS trades,
               COUNT(*) FILTER (WHERE t.transaction_type = 'P') AS buys,
               COUNT(*) FILTER (WHERE t.transaction_type = 'S') AS sells
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        WHERE {_VALID} AND t.notification_date >= CURRENT_DATE - CAST(:days AS INTEGER)
        GROUP BY m.id, m.full_name, m.party, m.state, m.chamber, m.district
        ORDER BY trades DESC, m.full_name
        LIMIT :lim
        """
    ), {"days": ACTIVE_WINDOW_DAYS, "lim": limit}).fetchall()
    return [{
        "member_id": str(r[0]), "member_name": r[1], "member_party": r[2], "member_state": r[3],
        "member_chamber": r[4], "member_district": r[5],
        "trades": int(r[6]), "buys": int(r[7]), "sells": int(r[8]),
    } for r in rows]


def _build_home() -> Dict[str, Any]:
    with get_sync_db_session() as s:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclosure_limit_days": DISCLOSURE_LIMIT_DAYS,
            "stats": _headline_stats(s),
            "latest": _latest_disclosures(s),
            "latest_window_days": LATEST_WINDOW_DAYS,
            "notable": _notable(s),
            "notable_window_days": NOTABLE_WINDOW_DAYS,
            "most_active": _most_active(s),
            "most_active_window_days": ACTIVE_WINDOW_DAYS,
        }


def _build_late(days: int, per_member: int) -> Dict[str, Any]:
    from sqlalchemy import text

    params = {"days": days, "limit": DISCLOSURE_LIMIT_DAYS}
    with get_sync_db_session() as s:
        rows = s.execute(text(
            f"""
            SELECT {_TRADE_COLUMNS} {_TRADE_FROM}
            WHERE {_VALID}
              AND t.notification_date >= CURRENT_DATE - CAST(:days AS INTEGER)
              AND {_LAG} > :limit AND {_NOT_AMENDED}
            ORDER BY {_LAG} DESC
            """
        ), params).fetchall()
        trades = [_trade_from_row(r) for r in rows]
        member_ids = sorted({t["member_id"] for t in trades})
        filings: Dict[str, int] = {}
        if member_ids:
            frows = s.execute(text(
                f"""
                SELECT CAST(t.member_id AS TEXT), COUNT(*)
                FROM congressional_trades t
                WHERE {_VALID}
                  AND t.notification_date >= CURRENT_DATE - CAST(:days AS INTEGER)
                  AND CAST(t.member_id AS TEXT) = ANY(:ids)
                GROUP BY t.member_id
                """
            ), {"days": days, "ids": member_ids}).fetchall()
            filings = {r[0]: int(r[1]) for r in frows}

    members = group_late_filers(trades, filings, per_member=per_member)
    lags = [t["days_to_disclose"] for t in trades if t["days_to_disclose"] is not None]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "disclosure_limit_days": DISCLOSURE_LIMIT_DAYS,
        "total_late": len(trades),
        "member_count": len(members),
        "median_days": int(round(median(lags))) if lags else None,
        "worst_days": max(lags) if lags else None,
        "members": members,
    }


# ====================================================================== routes
@router.get("/home", summary="Public homepage feed")
async def public_home():
    """Latest disclosures, headline stats, notable filings and the most
    active members. Anonymous; cached for 10 minutes."""
    data = await _cached("home", _build_home)
    return success_response(data=data)


@router.get("/late", summary="Late filings grouped by member")
async def public_late(
    days: int = Query(365, ge=30, le=3650, description="Filing-date window in days"),
    per_member: int = Query(50, ge=1, le=500, description="Max trades returned per member"),
):
    """Trades disclosed after the 45-day STOCK Act limit (amendments
    excluded), grouped by member with counts and worst / median lag."""
    data = await _cached(f"late:{days}:{per_member}", lambda: _build_late(days, per_member))
    return success_response(data=data)
