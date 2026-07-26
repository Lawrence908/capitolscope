"""
Sector enrichment for securities missing a GICS sector.

The Phase 0 universe seed created bare securities (ticker + name) for newly
matched symbols, leaving ``sector_gics_code`` null. The conflict engine needs a
sector per security, so this backfills it from yfinance's sector field, mapped
onto the 11 GICS sectors already present in the ``sectors`` table.

yfinance uses its own sector taxonomy; the map below aligns it to the GICS
names this database uses.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# yfinance sector -> our sectors.name
YF_TO_GICS = {
    "Technology": "Technology",
    "Financial Services": "Financials",
    "Healthcare": "Health Care",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Communication Services": "Communication Services",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Basic Materials": "Materials",
}


def enrich_missing_sectors_sync(session: Session, delay: float = 0.3, limit: int = None) -> Dict[str, Any]:
    # name -> gics_code lookup
    name_to_code = {
        r[0]: r[1] for r in session.execute(text("SELECT name, gics_code FROM sectors")).fetchall()
    }

    rows = session.execute(text(
        """
        SELECT DISTINCT se.id, se.ticker
        FROM securities se
        JOIN congressional_trades t ON t.security_id = se.id
        WHERE se.sector_gics_code IS NULL AND se.ticker IS NOT NULL
        """
    )).fetchall()
    if limit:
        rows = rows[:limit]

    stats = {"candidates": len(rows), "enriched": 0, "no_sector": 0, "failed": 0, "unmapped": 0}

    for i, (sec_id, ticker) in enumerate(rows, 1):
        try:
            info = yf.Ticker(ticker).info
            yf_sector = (info or {}).get("sector")
            if not yf_sector:
                stats["no_sector"] += 1
                continue
            gics_name = YF_TO_GICS.get(yf_sector)
            code = name_to_code.get(gics_name) if gics_name else None
            if not code:
                stats["unmapped"] += 1
                continue
            session.execute(
                text("UPDATE securities SET sector_gics_code = :c WHERE id = :id"),
                {"c": code, "id": sec_id},
            )
            stats["enriched"] += 1
        except Exception as exc:
            stats["failed"] += 1
            logger.debug("sector enrich failed for %s: %s", ticker, exc)

        if i % 50 == 0:
            session.commit()
            logger.info("sector enrichment %d/%d (enriched=%d)", i, len(rows), stats["enriched"])
        time.sleep(delay)

    session.commit()
    logger.info("Sector enrichment complete: %s", stats)
    return stats
