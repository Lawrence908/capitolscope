"""
Phase 4 (event study): earnings-proximity signal.

Positioning ahead of a known catalyst is the classic informed-trading pattern.
This module backfills historical earnings dates per traded security (yfinance,
~6 years / ~25 prints each) into a derived ``event_earnings`` table, then
measures how often a member trades in the window just *before* an earnings
release.

Legislation proximity (the other half of the roadmap's event factor) is
deliberately not built here: mapping bill actions to specific issuers with
enough signal-to-noise to be a fair flag is a separate, much larger effort
(thousands of routine actions per session), and a naive version would flag
almost everything. Earnings is the clean, per-ticker, well-defined event.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS event_earnings (
    security_id UUID NOT NULL,
    earnings_date DATE NOT NULL,
    source TEXT DEFAULT 'yfinance',
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (security_id, earnings_date)
);
"""

PRE_EARNINGS_WINDOW_DAYS = 10


def _ensure_table(session: Session) -> None:
    session.execute(text(_CREATE_TABLE))
    session.commit()


def backfill_earnings_dates_sync(session: Session, delay: float = 0.3, limit: int = None) -> Dict[str, Any]:
    """Fetch historical earnings dates for every traded security and upsert them
    into ``event_earnings``. Idempotent."""
    _ensure_table(session)

    rows = session.execute(text(
        """
        SELECT DISTINCT se.id, se.ticker
        FROM securities se
        JOIN congressional_trades t ON t.security_id = se.id
        WHERE se.ticker IS NOT NULL AND se.ticker <> ''
        """
    )).fetchall()
    if limit:
        rows = rows[:limit]

    stats = {"securities": len(rows), "with_dates": 0, "dates_upserted": 0, "failed": 0}

    for i, (sec_id, ticker) in enumerate(rows, 1):
        try:
            df = yf.Ticker(ticker).get_earnings_dates(limit=40)
            if df is None or df.empty:
                continue
            dates = sorted({d.date() for d in df.index})
            if not dates:
                continue
            session.execute(
                text(
                    "INSERT INTO event_earnings (security_id, earnings_date) "
                    "VALUES (:sid, :d) ON CONFLICT (security_id, earnings_date) DO NOTHING"
                ),
                [{"sid": sec_id, "d": d} for d in dates],
            )
            stats["with_dates"] += 1
            stats["dates_upserted"] += len(dates)
        except Exception as exc:
            stats["failed"] += 1
            logger.debug("earnings fetch failed for %s: %s", ticker, exc)

        if i % 50 == 0:
            session.commit()
            logger.info("earnings backfill %d/%d (with_dates=%d)", i, len(rows), stats["with_dates"])
        time.sleep(delay)

    session.commit()
    logger.info("Earnings backfill complete: %s", stats)
    return stats


def compute_member_event_proximity(
    session: Session,
    window_days: int = PRE_EARNINGS_WINDOW_DAYS,
    min_covered_trades: int = 5,
) -> Dict[str, Dict[str, Any]]:
    """Per-member pre-earnings positioning rate.

    A trade is "pre-earnings" when an earnings release falls within
    ``window_days`` *after* the transaction date (they traded before the print).
    The rate is over trades whose security actually has earnings coverage, so a
    member is not penalised for trading names we lack data for.

    Returns {member_name: {pre_earnings_trades, covered_trades, pre_earnings_rate}}.
    """
    # earnings dates per security
    ed_rows = session.execute(text(
        "SELECT security_id, earnings_date FROM event_earnings ORDER BY earnings_date"
    )).fetchall()
    earnings: Dict[Any, List] = defaultdict(list)
    for sid, d in ed_rows:
        earnings[sid].append(d)

    if not earnings:
        return {}

    trades = session.execute(text(
        """
        SELECT m.full_name, t.security_id, t.transaction_date
        FROM congressional_trades t
        JOIN congress_members m ON m.id = t.member_id
        WHERE t.security_id IS NOT NULL AND t.transaction_type IN ('P', 'S')
        """
    )).fetchall()

    import bisect
    agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"pre": 0, "covered": 0})
    for name, sid, tdate in trades:
        dates = earnings.get(sid)
        if not dates:
            continue
        agg[name]["covered"] += 1
        # first earnings date on/after the trade
        j = bisect.bisect_left(dates, tdate)
        if j < len(dates) and dates[j] <= tdate + timedelta(days=window_days):
            agg[name]["pre"] += 1

    out: Dict[str, Dict[str, Any]] = {}
    for name, a in agg.items():
        if a["covered"] < min_covered_trades:
            continue
        out[name] = {
            "pre_earnings_trades": a["pre"],
            "covered_trades": a["covered"],
            "pre_earnings_rate": round(a["pre"] / a["covered"], 4),
        }
    return out
