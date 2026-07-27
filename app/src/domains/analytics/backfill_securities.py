"""
Phase 0 security-matching backfill (WS1b + WS1c).

One pass over congressional trades that:

  1. Validates each trade's ticker against the active listed universe,
     preferring an explicit ``(SYMBOL)`` from the asset text.
  2. Seeds a ``securities`` row on demand for every valid traded symbol that is
     not already present (so we create exactly the ~1-2k symbols that actually
     appear, not the whole market).
  3. Sets ``congressional_trades.security_id`` and normalises the ``ticker``
     column to the validated symbol; clears tickers that are clearly parser
     noise (asset-type codes / non-symbol tokens).

Idempotent: re-running only fills gaps and fixes mismatches.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import re

from domains.congressional.models import CongressionalTrade
from domains.securities.models import Security
from domains.securities.matching import SecurityMatcher

logger = logging.getLogger(__name__)

# Mutual-fund symbols (5 letters ending in X, e.g. VFIAX) are real but are not
# in the listed-equity universe; keep them pending a dedicated fund universe
# rather than clearing them as junk.
_FUND_RE = re.compile(r"^[A-Z]{5}X$")

# Backfill stat key per resolution method returned by SecurityMatcher.resolve.
_METHOD_STAT = {
    "name": "name_matched",
    "alias": "alias_matched",
    "containment": "containment_matched",
    "fund": "fund_matched",
}


def backfill_security_matching_sync(
    session: Session,
    batch_size: int = 2000,
    dry_run: bool = False,
    matcher: Optional[SecurityMatcher] = None,
) -> Dict[str, Any]:
    """Re-resolve ``security_id`` for every congressional trade.

    Resolution is delegated to :class:`SecurityMatcher` (the same resolver live
    ingestion uses, so the two paths cannot drift). Pass a prebuilt ``matcher``
    to reuse its loaded universe/indexes; otherwise one is built here.

    With ``dry_run=True`` nothing is written: the same resolution waterfall runs
    and the stats report what *would* match, which is the projected match-rate
    accuracy measure (no securities are seeded, no trades are mutated).
    """
    if matcher is None:
        matcher = SecurityMatcher()

    # Preload existing securities: TICKER -> id
    sec_map: Dict[str, Any] = {}
    for sec in session.execute(select(Security)).scalars():
        if sec.ticker:
            sec_map.setdefault(sec.ticker.strip().upper(), sec.id)

    trades = session.execute(select(CongressionalTrade)).scalars().all()

    stats = {
        "trades_scanned": len(trades),
        "securities_created": 0,
        "security_id_set": 0,
        "ticker_normalised": 0,
        "ticker_cleared_as_junk": 0,
        "name_matched": 0,
        "alias_matched": 0,
        "containment_matched": 0,
        "fund_matched": 0,
        "unresolved": 0,
    }

    for i, trade in enumerate(trades, 1):
        symbol, method = matcher.resolve(trade.ticker, trade.raw_asset_description)
        if method in _METHOD_STAT:
            stats[_METHOD_STAT[method]] += 1

        if symbol:
            if dry_run:
                # Count what would match without seeding or mutating anything.
                if (trade.security_id is None
                        or (trade.ticker or "").strip().upper() != symbol):
                    stats["security_id_set"] += 1
                continue

            sid = sec_map.get(symbol)
            if sid is None:
                sec = Security(currency="USD", **matcher.security_seed(symbol, method, trade.asset_name))
                session.add(sec)
                session.flush()  # obtain generated id
                sid = sec.id
                sec_map[symbol] = sid
                stats["securities_created"] += 1

            if trade.security_id != sid:
                trade.security_id = sid
                stats["security_id_set"] += 1
            if (trade.ticker or "").strip().upper() != symbol:
                trade.ticker = symbol
                stats["ticker_normalised"] += 1
        else:
            stats["unresolved"] += 1
            if dry_run:
                continue
            # Enforce the invariant "ticker column holds a validated symbol or
            # null". Resolution already failed against the parenthetical and the
            # listed universe, so a leftover ticker is name-word noise (GROUP,
            # CLASS, TEXAS, ...) or a delisted symbol we cannot currently stand
            # behind. Keep mutual-fund symbols for a future fund-universe pass;
            # clear everything else (the full asset text is retained regardless).
            if trade.ticker:
                tk = trade.ticker.strip().upper()
                if not _FUND_RE.match(tk):
                    # The ticker was junk, so any security_id derived from it is a
                    # wrong match (e.g. "AstraZeneca PLC" mapped to Park Lawn via
                    # the PLC suffix). Clear both, not just the ticker.
                    trade.ticker = None
                    if trade.security_id is not None:
                        trade.security_id = None
                        stats["security_id_cleared"] = stats.get("security_id_cleared", 0) + 1
                    stats["ticker_cleared_as_junk"] += 1

        if not dry_run and i % batch_size == 0:
            session.commit()
            logger.info("backfill progress: %d/%d", i, len(trades))

    if dry_run:
        stats["would_match_total"] = stats["trades_scanned"] - stats["unresolved"]
        stats["match_rate_pct"] = round(
            100.0 * stats["would_match_total"] / max(1, stats["trades_scanned"]), 1
        )
        logger.info("Security matching DRY RUN: %s", stats)
        session.rollback()
        return stats

    session.commit()
    logger.info("Security matching backfill complete: %s", stats)
    return stats
