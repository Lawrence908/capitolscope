"""
Phase 0 trade-return backfill (WS2b).

For every matched trade, derive from ``daily_prices``:
  - ``price_at_trade``      close on the first trading day on/after the
                            transaction date (stored in cents).
  - ``price_change_1d``     forward return at ~1 / 7 / 30 calendar days
  - ``price_change_7d``     after the trade (fractional, e.g. 0.0234), each
  - ``price_change_30d``    measured against the trade-date close.

Processed per security so each price series is loaded once. "Forward N days"
resolves to the first trading day on/after (transaction_date + N days) via
binary search, so weekends/holidays are handled.
"""

from __future__ import annotations

import bisect
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_FORWARD = {"price_change_1d": 1, "price_change_7d": 7, "price_change_30d": 30}

# price_change_* is Decimal(8,6): |value| must be < 100 (i.e. < 10000%). Any
# computed return beyond this cap is a data artifact (unadjusted split, a bad
# bar, or a wrong security mapping), not a real move, so we drop it rather than
# store a garbage number or overflow the column.
_MAX_ABS_RETURN = 9.999999


def _forward_at(dates: List, series: List, target) -> Any:
    """Value on the first trading day on/after ``target`` (or None)."""
    i = bisect.bisect_left(dates, target)
    return series[i] if i < len(dates) else None


def backfill_trade_returns_sync(
    session: Session,
    batch_commit: int = 25,
    recent_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Populate price_at_trade and forward returns for matched trades.

    ``recent_days``: if set, only (re)price trades whose transaction_date is
    within the last N days OR that are still missing a 30d return. This keeps
    the scheduled daily refresh cheap while filling forward windows as they
    mature; ``None`` reprices everything (full backfill).
    """
    trade_filter = ""
    params: Dict[str, Any] = {}
    if recent_days is not None:
        trade_filter = (
            " AND (t.transaction_date >= (CURRENT_DATE - CAST(:rd AS INTEGER)) "
            "OR t.price_change_30d IS NULL)"
        )
        params["rd"] = recent_days

    # Securities that have both in-scope trades and price history.
    sec_ids = [r[0] for r in session.execute(text(
        f"""
        SELECT DISTINCT t.security_id
        FROM congressional_trades t
        WHERE t.security_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM daily_prices dp WHERE dp.security_id = t.security_id)
          {trade_filter}
        """
    ), params).fetchall()]

    stats = {"securities": len(sec_ids), "trades_priced": 0, "returns_set": 0,
             "no_price_on_date": 0, "returns_skipped_outlier": 0}

    for n, sid in enumerate(sec_ids, 1):
        prices = session.execute(text(
            "SELECT price_date, close_price, adjusted_close FROM daily_prices "
            "WHERE security_id = :sid ORDER BY price_date"
        ), {"sid": sid}).fetchall()
        if not prices:
            continue
        dates = [p[0] for p in prices]
        # Raw close for the recorded trade price; adjusted close (split/dividend
        # aware) for the return math so corporate actions don't fake huge moves.
        closes = [float(p[1]) for p in prices]
        adj = [float(p[2]) if p[2] is not None else float(p[1]) for p in prices]

        trades = session.execute(text(
            f"SELECT id, transaction_date FROM congressional_trades t "
            f"WHERE security_id = :sid {trade_filter}"
        ), {"sid": sid, **params}).fetchall()

        for trade_id, txn_date in trades:
            base_raw = _forward_at(dates, closes, txn_date)
            base_adj = _forward_at(dates, adj, txn_date)
            if not base_raw or base_raw <= 0 or not base_adj or base_adj <= 0:
                stats["no_price_on_date"] += 1
                continue

            updates = {"price_at_trade": int(round(base_raw * 100))}
            for col, days in _FORWARD.items():
                fwd = _forward_at(dates, adj, txn_date + timedelta(days=days))
                if not fwd:
                    continue
                ret = fwd / base_adj - 1.0
                if abs(ret) > _MAX_ABS_RETURN:
                    stats["returns_skipped_outlier"] += 1
                    continue
                updates[col] = round(Decimal(str(ret)), 6)
                stats["returns_set"] += 1

            set_clause = ", ".join(f"{c} = :{c}" for c in updates)
            session.execute(
                text(f"UPDATE congressional_trades SET {set_clause} WHERE id = :id"),
                {**updates, "id": trade_id},
            )
            stats["trades_priced"] += 1

        if n % batch_commit == 0:
            session.commit()
            logger.info("trade-return backfill %d/%d securities", n, len(sec_ids))

    session.commit()
    logger.info("Trade-return backfill complete: %s", stats)
    return stats
