"""
Ticker validation / cleaning.

The disclosure parser extracts a ``ticker`` per trade, but for ~half of the
distinct values it picks up name-words rather than symbols: GROUP, CLASS, LP,
BANK, ADR, SPDR, plus asset-type codes leaking from the ``[ST]`` / ``[OI]``
tags. These pollute security matching and every downstream join.

The primary gate is membership in the active listed universe (see
``universe.fetch_active_us_tickers``): a token is a real ticker only if it is a
real, currently listed symbol. That single rule rejects the noise while keeping
legitimate short tickers that happen to be English words (ALL, ON, SO, IT, DD).
A small stoplist covers disclosure-specific artifacts (asset-type codes) that
are not worth round-tripping through the universe check.
"""

from __future__ import annotations

import re
from typing import Optional, Set

# Disclosure-form artifacts that are never tickers. Kept deliberately small;
# the universe check does the heavy lifting so we don't risk rejecting real
# one/two-letter symbols.
ASSET_TYPE_CODES = {
    "ST", "OP", "OI", "PS", "OL", "RP", "PE", "HN", "AB", "CS", "GS", "EF",
    "MF", "OT", "CT", "FA", "BA", "ST.", "OI.",
}

# Legal-form suffixes the parser sometimes lifts off a company name ("AstraZeneca
# PLC", "X GmbH") and mistakes for a ticker. Several collide with a real but
# obscure/delisted listing (PLC -> Park Lawn), producing wrong matches. These are
# essentially never the intended US ticker, so reject them outright. (AG, SA, U
# are deliberately NOT here: they are real, actively-traded tickers even though
# they also appear as suffixes, so disambiguating them needs name matching.)
CORPORATE_FORM_SUFFIXES = {
    "PLC", "ADR", "NV", "GMBH", "LTD", "LP", "AB", "ASA", "OYJ", "SPA",
    "BV", "AS", "OY", "KK", "PT", "TBK", "SAB", "AE",
}

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,6}$")
_PAREN_TICKER_RE = re.compile(r"\(([A-Z]{1,6}(?:[.\-][A-Z]{1,3})?)\)")

# Open-end mutual & money-market fund symbols are 5 letters ending in X by FINRA
# convention (VFIAX, TDDXX). They are not in the listed-equity/OTC universe, but
# the symbol embedded in the disclosure text is itself authoritative.
_FUND_TICKER_RE = re.compile(r"\b([A-Z]{4}X)\b")
# Fund-context cue: only trust a 5-letter/X token when the text reads like a fund.
_FUND_CONTEXT_RE = re.compile(
    r"\b(fund|fedfund|money market|money mkt|portfolio|treasury|income|"
    r"index|trust|shares|admiral|investor|institutional)\b",
    re.I,
)
# Common 5-letter words ending in X that are not fund symbols.
_FUND_STOPWORDS = {"INDEX", "XEROX", "FEDEX", "RELAX", "LATEX", "ANNEX", "HELIX"}


def extract_fund_ticker(text: Optional[str]) -> Optional[str]:
    """Return an embedded 5-letter mutual/money-market fund symbol (…X), or None.

    Guards against false positives (the word "INDEX" also fits …X): the text must
    read like a fund, and the symbol is the *last* qualifying token ("BLF FedFund
    TDDXX" -> TDDXX; funds place the symbol at the end), excluding common words.
    """
    if not text:
        return None
    up = text.upper()
    if not _FUND_CONTEXT_RE.search(text):
        return None
    candidates = [m for m in _FUND_TICKER_RE.findall(up) if m not in _FUND_STOPWORDS]
    return candidates[-1] if candidates else None


def looks_like_ticker(token: str) -> bool:
    """Cheap structural check before the (authoritative) universe lookup."""
    if not token:
        return False
    t = token.strip().upper()
    if t in ASSET_TYPE_CODES or t in CORPORATE_FORM_SUFFIXES:
        return False
    return bool(_TICKER_RE.match(t))


def extract_paren_ticker(text: str) -> Optional[str]:
    """Prefer an explicit parenthetical symbol from the raw asset text, e.g.
    'Intel Corporation - Common Stock (INTC)' -> 'INTC'."""
    if not text:
        return None
    m = _PAREN_TICKER_RE.search(text)
    return m.group(1).upper() if m else None


def resolve_ticker(
    raw_ticker: Optional[str],
    raw_asset: Optional[str],
    universe: Set[str],
) -> Optional[str]:
    """Return a validated ticker or ``None``.

    Order of preference:
      1. An explicit ``(SYMBOL)`` in the asset text that is in the universe.
      2. The parser's ``raw_ticker`` if it is in the universe.
    Anything not confirmed by the universe is rejected (returns ``None``),
    which is how GROUP / CLASS / SPDR / asset-type codes get filtered.
    """
    paren = extract_paren_ticker(raw_asset or "")
    if paren and paren in universe and paren not in CORPORATE_FORM_SUFFIXES:
        return paren

    if raw_ticker:
        t = raw_ticker.strip().upper()
        if looks_like_ticker(t) and t in universe:
            return t

    return None
