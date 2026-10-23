"""
Pure helpers for the public trade pages (trade permalink, ticker page, feeds).

Kept free of database and framework imports so they can be unit-tested in
isolation. Amounts stay in cents (as stored); prices from ``daily_prices`` are
whole dollars (see the price-units note in the securities models).
"""

from __future__ import annotations

import bisect
import re
from datetime import date
from typing import Any, Iterable, List, Optional, Sequence, Tuple

# STOCK Act: a transaction must be disclosed within 45 days.
DISCLOSURE_LIMIT_DAYS = 45

HOUSE_PTR_PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
SENATE_PTR_URL = "https://efdsearch.senate.gov/search/view/ptr/{doc_id}/"

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_HOUSE_DOC_RE = re.compile(r"^\d{5,10}$")


def _norm_chamber(chamber: Any) -> Optional[str]:
    value = getattr(chamber, "value", chamber)
    if not value:
        return None
    text = str(value).strip().lower()
    if text.startswith("s"):
        return "Senate"
    if text.startswith("h"):
        return "House"
    return None


def infer_chamber(chamber: Any, doc_id: Optional[str]) -> Optional[str]:
    """The member's chamber, falling back to the filing's document id format.

    House Clerk PTR ids are numeric (e.g. ``20027931``); Senate eFD report ids
    are UUIDs. Many former members have no chamber recorded, but every trade
    carries the id of the filing it came from.
    """
    known = _norm_chamber(chamber)
    if known:
        return known
    doc = (doc_id or "").strip()
    if _UUID_RE.match(doc):
        return "Senate"
    if _HOUSE_DOC_RE.match(doc):
        return "House"
    return None


def filing_document_url(
    doc_id: Optional[str],
    document_url: Optional[str] = None,
    filing_date: Optional[date] = None,
    chamber: Any = None,
) -> Optional[str]:
    """Link to the original disclosure.

    Uses the stored ``document_url`` when present; otherwise derives it from the
    document id the same way the fetchers locate filings: House PTR PDFs live at
    ``ptr-pdfs/<filing year>/<doc_id>.pdf`` on the Clerk site, Senate electronic
    PTRs at ``efdsearch.senate.gov/search/view/ptr/<uuid>/``.
    """
    if document_url and document_url.strip():
        return document_url.strip()
    doc = (doc_id or "").strip()
    if not doc:
        return None
    if _UUID_RE.match(doc):
        return SENATE_PTR_URL.format(doc_id=doc.lower())
    if _HOUSE_DOC_RE.match(doc) and filing_date is not None and infer_chamber(chamber, doc) == "House":
        return HOUSE_PTR_PDF_URL.format(year=filing_date.year, doc_id=doc)
    return None


def days_to_disclose(transaction_date: Optional[date], notification_date: Optional[date]) -> Optional[int]:
    """Whole days from trade to disclosure, never negative; None if unknown."""
    if not transaction_date or not notification_date:
        return None
    return max(0, (notification_date - transaction_date).days)


def is_amended(filing_status: Any) -> bool:
    value = getattr(filing_status, "value", filing_status)
    return str(value or "").strip().upper().startswith("A")


def is_late(days: Optional[int], amended: bool = False) -> bool:
    """Past the 45-day limit. Amended filings are never counted as late: their
    filing date reflects the amendment, not the original disclosure."""
    return (not amended) and days is not None and days > DISCLOSURE_LIMIT_DAYS


def downsample(points: Sequence[Any], max_points: int) -> List[Any]:
    """Evenly thin a series to at most ``max_points``, always keeping the last
    point (the most recent close) and the first."""
    n = len(points)
    if max_points <= 0:
        return []
    if n <= max_points:
        return list(points)
    if max_points == 1:
        return [points[-1]]
    step = (n - 1) / (max_points - 1)
    idx = sorted({round(i * step) for i in range(max_points)} | {0, n - 1})
    return [points[i] for i in idx]


def price_on_or_before(series: Sequence[Tuple[date, Any]], target: Optional[date]) -> Optional[Any]:
    """Close on ``target`` or the nearest earlier trading day. ``series`` must
    be sorted ascending by date."""
    if target is None or not series:
        return None
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, target) - 1
    if i < 0:
        return None
    return series[i][1]


def summarize_ticker_trades(trades: Iterable[dict]) -> dict:
    """Headline stats for a ticker page from feed-shaped trade dicts."""
    rows = list(trades)
    members = {t.get("member_id") for t in rows if t.get("member_id")}
    buys = sum(1 for t in rows if (t.get("transaction_type") or "").upper().startswith("P"))
    sells = sum(1 for t in rows if (t.get("transaction_type") or "").upper().startswith("S"))
    tdates = [t["transaction_date"] for t in rows if t.get("transaction_date")]
    ndates = [t["notification_date"] for t in rows if t.get("notification_date")]
    late = sum(
        1
        for t in rows
        if is_late(t.get("days_to_disclose"), is_amended(t.get("filing_status")))
    )
    return {
        "trades": len(rows),
        "members": len(members),
        "buys": buys,
        "sells": sells,
        "other": len(rows) - buys - sells,
        "late": late,
        "first_trade_date": min(tdates) if tdates else None,
        "latest_trade_date": max(tdates) if tdates else None,
        "latest_filing_date": max(ndates) if ndates else None,
    }
