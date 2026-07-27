"""
Company-name -> ticker resolution.

Most un-tickered congressional trades are plain company names ("NextEra Energy,
Inc", "3M Company") whose ticker was never parsed. The listed universe already
carries a name per symbol, so we can recover the ticker by normalizing both
sides and matching. Deliberately conservative: only *exact* normalized matches,
and ambiguous normalized names (mapping to >1 ticker) are skipped — a wrong
security_id silently corrupts every portfolio/return, so precision beats recall.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Set

# Legal-form / boilerplate tokens stripped from the end (or anywhere) of a name
# so both sides normalize identically.
_SUFFIX_TOKENS = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "companies",
    "ltd", "limited", "plc", "llc", "lp", "llp", "sa", "nv", "ag", "se",
    "trust", "the",
    # Fund/ETF boilerplate — lets "SPDR Gold Trust" match "SPDR Gold Shares",
    # "X ETF" match "X", etc. Verified net-positive with no stock regression.
    "etf", "fund", "index", "shares",
}
_BOILERPLATE = [
    "common stock", "ordinary shares", "class a", "class b", "class c",
    "depositary shares", "american depositary", "adr", "reit",
]
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def normalize_company_name(name: Optional[str]) -> str:
    """Normalize a company name to a comparable key ('' if nothing usable)."""
    if not name:
        return ""
    s = name.lower()
    s = s.replace("&", " and ")
    for phrase in _BOILERPLATE:
        s = s.replace(phrase, " ")
    s = _PUNCT_RE.sub(" ", s)
    tokens = [t for t in _WS_RE.sub(" ", s).strip().split(" ") if t and t not in _SUFFIX_TOKENS]
    return " ".join(tokens)


def build_name_index(universe_meta: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """normalized name -> ticker, dropping names that map to more than one symbol."""
    counts: Dict[str, Set[str]] = {}
    for symbol, meta in universe_meta.items():
        key = normalize_company_name(meta.get("name"))
        if not key:
            continue
        counts.setdefault(key, set()).add(symbol.strip().upper())
    return {key: next(iter(syms)) for key, syms in counts.items() if len(syms) == 1}


def resolve_ticker_by_name(raw_asset: Optional[str], name_index: Dict[str, str]) -> Optional[str]:
    """Resolve a ticker from an asset description via exact normalized-name match."""
    key = normalize_company_name(raw_asset)
    if not key:
        return None
    return name_index.get(key)
