"""
Shared security resolver used by both the batch backfill and live ingestion.

Centralises the resolution waterfall so the two paths can never drift:

    validated ticker/paren  ->  exact company name  ->  curated alias
    ->  token-containment    ->  embedded fund symbol

with the precision guards that keep the match rate honest:

  * fixed-income descriptions (bonds/notes/treasuries/municipals) never match an
    equity — not even via a stored 1-2 letter ticker;
  * names whose historical ticker was reused by an unrelated active company are
    re-resolved from the raw name (so the stored ticker can't mislink);
  * preferred / fixed-income listings are excluded as name-match targets.

Build one :class:`SecurityMatcher` (it loads the universe + indexes once) and
call :meth:`resolve` per trade.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

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
from domains.securities.ticker_cleaning import extract_fund_ticker, resolve_ticker
from domains.securities.universe import load_universe, select_matchable

logger = logging.getLogger(__name__)

# Company names whose historical ticker has since been REUSED by an unrelated
# active company (Monsanto's MON is now a 2022 SPAC; Anadarko's APC is now ARKO;
# Praxair's PX is P10; Sprint's S is SentinelOne; ...). A previously-stored ticker
# validates against the (active, wrong) listing, so ignore it and resolve only
# from the raw name — which no longer aliases anywhere -> correctly unmatched.
REUSED_TICKER_NAMES = {
    "monsanto", "anadarko petroleum", "praxair", "sprint", "delphi automotive",
    "semgroup", "pluralsight", "suntrust banks", "golden ocean group",
}


class SecurityMatcher:
    """Resolves a disclosure (raw ticker + asset text) to a validated symbol."""

    def __init__(self, universe_meta: Optional[Dict[str, Dict[str, str]]] = None):
        raw = universe_meta if universe_meta is not None else load_universe(include_delisted=True)
        self.universe_meta = select_matchable(raw)
        self.universe = set(self.universe_meta)
        # Name-match targets exclude preferred / fixed-income listings so they
        # can't shadow a renamed common stock.
        common_meta = {s: v for s, v in self.universe_meta.items() if is_common_equity_target(v)}
        self.name_index = build_name_index(common_meta)
        self.containment_index = build_containment_index(self.name_index)
        self.alias_index = build_alias_index(self.universe)
        active_n = sum(1 for v in self.universe_meta.values() if v.get("active", True))
        logger.info(
            "SecurityMatcher ready: %d matchable (%d active / %d delisted), "
            "%d name keys, %d aliases",
            len(self.universe), active_n, len(self.universe) - active_n,
            len(self.name_index), len(self.alias_index),
        )

    def resolve(self, raw_ticker: Optional[str], raw_asset: Optional[str]) -> Tuple[Optional[str], str]:
        """Resolve to ``(symbol, method)``.

        ``method`` is one of ``ticker``/``name``/``alias``/``containment``/``fund``
        on success, or ``fixed_income``/``unresolved`` when no equity match is made.
        """
        is_fixed_income = looks_like_fixed_income(raw_asset)

        if not is_fixed_income:
            stored = raw_ticker
            if normalize_company_name(raw_asset) in REUSED_TICKER_NAMES:
                stored = None
            symbol = resolve_ticker(stored, raw_asset, self.universe)
            if symbol:
                return symbol, "ticker"

            symbol = resolve_ticker_by_name(raw_asset, self.name_index)
            if symbol:
                return symbol, "name"

            symbol = resolve_ticker_by_alias(normalize_company_name(raw_asset), self.alias_index)
            if symbol:
                return symbol, "alias"

            symbol = resolve_ticker_by_containment(raw_asset, self.name_index, self.containment_index)
            if symbol:
                return symbol, "containment"

        # Fund symbols (…X) are authoritative from the text and legitimately carry
        # fund-context words ("treasury"/"income"), so they run even for FI text.
        symbol = extract_fund_ticker(raw_asset)
        if symbol:
            return symbol, "fund"

        return None, "fixed_income" if is_fixed_income else "unresolved"

    def security_seed(self, symbol: str, method: str, fallback_name: Optional[str] = None) -> Dict[str, object]:
        """Fields for seeding a ``Security`` row for ``symbol`` (fund symbols are
        typed MF; delisted symbols are flagged ``is_active=False``)."""
        meta = self.universe_meta.get(symbol, {})
        return {
            "ticker": symbol,
            "name": (meta.get("name") or fallback_name or symbol)[:200],
            "asset_type_code": "MF" if method == "fund" else meta.get("asset_type", "STOCK"),
            "is_active": bool(meta.get("active", True)),
        }
