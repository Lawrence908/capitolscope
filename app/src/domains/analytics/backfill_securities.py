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
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

import re

from domains.congressional.models import CongressionalTrade
from domains.securities.models import Security
from domains.securities.ticker_cleaning import extract_fund_ticker, resolve_ticker
from domains.securities.name_matching import (
    build_containment_index,
    build_name_index,
    is_common_equity_target,
    looks_like_fixed_income,
    normalize_company_name,
    resolve_ticker_by_containment,
    resolve_ticker_by_name,
)
from domains.securities.historical_aliases import build_alias_index, resolve_ticker_by_alias
from domains.securities.universe import load_universe, select_matchable

logger = logging.getLogger(__name__)

# Mutual-fund symbols (5 letters ending in X, e.g. VFIAX) are real but are not
# in the listed-equity universe; keep them pending a dedicated fund universe
# rather than clearing them as junk.
_FUND_RE = re.compile(r"^[A-Z]{5}X$")

# Company names whose historical ticker has since been REUSED by an unrelated
# active company (Monsanto's MON is now a 2022 SPAC; Anadarko's APC is now ARKO;
# Praxair's PX is P10; Sprint's S is SentinelOne; ...). Earlier alias passes wrote
# these wrong tickers to the trades, and because the stored ticker validates
# against the (active, wrong) listing, a normal re-run would keep the bad match.
# Force re-resolution from the raw name for these so the removed alias actually
# takes effect and they revert to unmatched (correct: better null than wrong).
_REUSED_TICKER_NAMES = {
    "monsanto", "anadarko petroleum", "praxair", "sprint", "delphi automotive",
    "semgroup", "pluralsight", "suntrust banks", "golden ocean group",
}


def backfill_security_matching_sync(
    session: Session, batch_size: int = 2000, dry_run: bool = False
) -> Dict[str, Any]:
    """Re-resolve ``security_id`` for every congressional trade.

    With ``dry_run=True`` nothing is written: the same resolution waterfall runs
    and the stats report what *would* match, which is the projected match-rate
    accuracy measure (no securities are seeded, no trades are mutated).
    """
    # Active + delisted universe: delisted symbols are what let historical trades
    # (Twitter, Celgene, United Technologies, ...) resolve to a security. Restrict
    # to matchable symbols (drops reused-ticker collisions and pre-2011 junk).
    universe_meta = select_matchable(load_universe(include_delisted=True))
    universe = set(universe_meta.keys())
    # Name-match targets exclude preferred / fixed-income listings so they can't
    # shadow a renamed common stock.
    common_meta = {s: v for s, v in universe_meta.items() if is_common_equity_target(v)}
    # Company-name -> ticker index (recovers un-tickered trades that are plain
    # company names, e.g. "NextEra Energy, Inc").
    name_index = build_name_index(common_meta)
    # Token sub/superset index for verbose or lightly-renamed listing names
    # ("Taiwan Semiconductor" vs "...Manufacturing Company").
    containment_index = build_containment_index(name_index)
    # Curated rename/alias map for names that changed too much to match by
    # normalization alone ("Priceline Group" -> BKNG, "Dominion Resources" -> D).
    alias_index = build_alias_index(universe)
    active_n = sum(1 for v in universe_meta.values() if v.get("active", True))
    logger.info(
        "Universe: %d matchable (%d active / %d delisted), %d name keys, %d aliases",
        len(universe), active_n, len(universe) - active_n, len(name_index), len(alias_index),
    )

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
        symbol = None
        # Bonds/notes/treasuries/municipals are not equities and must never match
        # a stock ticker — not even via a stored 1-2 letter ticker that happens to
        # be a real symbol (a "Monsanto ... 2.125%" bond once matched Barrick "B").
        is_fixed_income = looks_like_fixed_income(trade.raw_asset_description)

        if not is_fixed_income:
            # For names whose old ticker was reused by an unrelated active company,
            # ignore any previously-stored ticker so resolution comes only from the
            # raw name (which no longer aliases anywhere -> correctly unmatched).
            stored_ticker = trade.ticker
            if normalize_company_name(trade.raw_asset_description) in _REUSED_TICKER_NAMES:
                stored_ticker = None
            symbol = resolve_ticker(stored_ticker, trade.raw_asset_description, universe)

        # Fallback 1: recover a ticker from the company name for un-tickered trades.
        if not symbol and not is_fixed_income:
            name_symbol = resolve_ticker_by_name(trade.raw_asset_description, name_index)
            if name_symbol:
                symbol = name_symbol
                stats["name_matched"] += 1

        # Fallback 2: curated rename/alias map (renamed or mangled names).
        if not symbol and not is_fixed_income:
            alias_symbol = resolve_ticker_by_alias(
                normalize_company_name(trade.raw_asset_description), alias_index
            )
            if alias_symbol:
                symbol = alias_symbol
                stats["alias_matched"] += 1

        # Fallback 3: token sub/superset containment against one listing name.
        if not symbol:
            contain_symbol = resolve_ticker_by_containment(
                trade.raw_asset_description, name_index, containment_index
            )
            if contain_symbol:
                symbol = contain_symbol
                stats["containment_matched"] += 1

        # Fallback 4: embedded mutual/money-market fund symbol (…X). The symbol in
        # the disclosure text is itself authoritative (not in the equity universe).
        fund_symbol = None
        if not symbol:
            fund_symbol = extract_fund_ticker(trade.raw_asset_description)
            if fund_symbol:
                symbol = fund_symbol
                stats["fund_matched"] += 1

        if symbol:
            if dry_run:
                # Count what would match without seeding or mutating anything.
                if (trade.security_id is None
                        or (trade.ticker or "").strip().upper() != symbol):
                    stats["security_id_set"] += 1
                continue

            sid = sec_map.get(symbol)
            if sid is None:
                meta = universe_meta.get(symbol, {})
                # Fund symbols aren't in the equity universe; type them as MF.
                asset_type_code = "MF" if fund_symbol else meta.get("asset_type", "STOCK")
                sec = Security(
                    ticker=symbol,
                    name=(meta.get("name") or trade.asset_name or symbol)[:200],
                    asset_type_code=asset_type_code,
                    currency="USD",
                    # Flag delisted symbols so downstream (price fetch, UI) can
                    # tell a live listing from a historical one.
                    is_active=bool(meta.get("active", True)),
                )
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
