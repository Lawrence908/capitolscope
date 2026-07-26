"""
Phase 0 daily-price backfill (WS2a).

Fetches daily OHLCV history (yfinance) for every security actually referenced
by a matched congressional trade, plus the SPY benchmark, and writes it to
``daily_prices``. yfinance returns a security's full history in a single call,
so the cost scales with the number of distinct tickers (~800), not the date
range. Idempotent: existing (security_id, price_date) rows are skipped.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yfinance as yf
from sqlalchemy import select, text
from sqlalchemy.orm import Session

# NB: the properly-mapped SQLAlchemy DailyPrice lives in securities.models
# (market_data.models has a same-named non-ORM placeholder bound to the same
# table). The price ingestion task imports it from here too.
from domains.securities.models import Security, DailyPrice

logger = logging.getLogger(__name__)

BENCHMARKS = ["SPY"]  # market benchmark for later abnormal-return work


def _tickers_to_backfill(session: Session) -> Dict[str, Any]:
    """Return {TICKER: security_id} for securities referenced by matched trades,
    plus benchmarks (created if missing)."""
    rows = session.execute(text(
        """
        SELECT DISTINCT se.ticker, se.id
        FROM securities se
        JOIN congressional_trades t ON t.security_id = se.id
        WHERE se.ticker IS NOT NULL AND se.ticker <> ''
        """
    )).fetchall()
    mapping = {r[0].strip().upper(): r[1] for r in rows}

    for bt in BENCHMARKS:
        if bt not in mapping:
            sec = session.execute(select(Security).where(Security.ticker == bt)).scalar_one_or_none()
            if sec is None:
                sec = Security(ticker=bt, name=f"{bt} (benchmark)", asset_type_code="ETF", currency="USD")
                session.add(sec)
                session.flush()
            mapping[bt] = sec.id
    session.commit()
    return mapping


def backfill_prices_sync(
    session: Session,
    start: str = "2015-01-01",
    end: Optional[str] = None,
    delay: float = 0.4,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    mapping = _tickers_to_backfill(session)
    tickers: List[str] = list(mapping.keys())
    if limit:
        tickers = tickers[:limit]

    stats = {"tickers": len(tickers), "ok": 0, "failed": 0, "rows_inserted": 0, "skipped_existing": 0}

    for idx, ticker in enumerate(tickers, 1):
        security_id = mapping[ticker]
        try:
            existing = {
                r[0] for r in session.execute(
                    text("SELECT price_date FROM daily_prices WHERE security_id = :sid"),
                    {"sid": security_id},
                ).fetchall()
            }
            hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
            if hist is None or hist.empty:
                stats["failed"] += 1
                continue

            payload = []
            for ts, row in hist.iterrows():
                d = ts.date()
                if d in existing:
                    stats["skipped_existing"] += 1
                    continue
                close = row.get("Close")
                if close is None or close != close:  # NaN guard
                    continue
                payload.append({
                    "id": uuid4(),
                    "security_id": security_id,
                    "price_date": d,
                    "open_price": Decimal(str(round(float(row["Open"]), 4))),
                    "high_price": Decimal(str(round(float(row["High"]), 4))),
                    "low_price": Decimal(str(round(float(row["Low"]), 4))),
                    "close_price": Decimal(str(round(float(close), 4))),
                    "adjusted_close": Decimal(str(round(float(row.get("Adj Close", close)), 4))),
                    "volume": int(row.get("Volume", 0) or 0),
                    "split_factor": Decimal("1.0"),
                    "dividend_amount": Decimal("0.0"),
                })
            if payload:
                # Core bulk insert bypasses the ORM constructor and is far faster
                # for the ~hundreds-of-thousands of bars this backfill writes.
                session.execute(DailyPrice.__table__.insert(), payload)
            session.commit()
            new_rows = len(payload)
            stats["ok"] += 1
            stats["rows_inserted"] += new_rows
        except Exception as exc:
            session.rollback()
            stats["failed"] += 1
            logger.warning("price backfill failed for %s: %s", ticker, exc)

        if idx % 25 == 0:
            logger.info("price backfill %d/%d (rows=%d)", idx, len(tickers), stats["rows_inserted"])
        time.sleep(delay)

    logger.info("Price backfill complete: %s", stats)
    return stats
