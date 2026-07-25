"""
Active US securities universe.

Used as (a) the seed for the ``securities`` table and (b) the validation oracle
that decides whether a parsed "ticker" is a real listed symbol. Membership in
this set is what separates genuine tickers (``ALL``, ``ON``, ``SO``) from the
name-word noise the disclosure parser sometimes emits (``GROUP``, ``CLASS``,
``SPDR``, ``ADR``).

Primary source is the Nasdaq Trader symbol directory (nasdaqlisted + otherlisted):
free, no API key, no rate limit, and covers NASDAQ + NYSE + AMEX + ARCA
(~13k symbols including ETFs). Polygon reference tickers is kept as an optional
fallback but is rate-limited on the free tier.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Dict

logger = logging.getLogger(__name__)

_NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
_OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
_HEADERS = {"User-Agent": "Mozilla/5.0 (capitolscope-universe)"}

_POLYGON_BASE = "https://api.polygon.io/v3/reference/tickers"
_TYPE_TO_ASSET = {
    "CS": "STOCK", "ADRC": "STOCK", "ADRP": "STOCK", "PFD": "PFD",
    "ETF": "ETF", "ETN": "ETF", "ETV": "ETF", "FUND": "ETF", "REIT": "REIT",
}


def _fetch_text(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("latin-1")


def _parse_pipe_file(text: str, symbol_col: int, name_col: int, etf_col: int, test_col: int) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    lines = text.splitlines()
    if not lines:
        return out
    for line in lines[1:]:  # skip header
        # The file ends with a "File Creation Time" footer line with no pipes.
        if "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) <= max(symbol_col, name_col, etf_col, test_col):
            continue
        if parts[test_col].strip().upper() == "Y":  # test issue, not tradable
            continue
        symbol = parts[symbol_col].strip().upper()
        if not symbol or any(c in symbol for c in "$^ "):  # warrants/units/junk
            continue
        etf = parts[etf_col].strip().upper() == "Y"
        out.setdefault(symbol, {
            "name": parts[name_col].strip()[:200],
            "asset_type": "ETF" if etf else "STOCK",
            "poly_type": "",
        })
    return out


def fetch_active_us_tickers() -> Dict[str, Dict[str, str]]:
    """Return {TICKER: {"name", "asset_type", "poly_type"}} from Nasdaq Trader."""
    universe: Dict[str, Dict[str, str]] = {}

    # nasdaqlisted: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot|ETF|NextShares
    universe.update(_parse_pipe_file(_fetch_text(_NASDAQ_LISTED), symbol_col=0, name_col=1, etf_col=6, test_col=3))
    # otherlisted: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot|Test Issue|NASDAQ Symbol
    for sym, meta in _parse_pipe_file(_fetch_text(_OTHER_LISTED), symbol_col=0, name_col=1, etf_col=4, test_col=6).items():
        universe.setdefault(sym, meta)

    logger.info("Nasdaq Trader universe: %d symbols", len(universe))
    if len(universe) < 3000:
        raise RuntimeError(f"Universe suspiciously small ({len(universe)}); refusing to use for validation")
    return universe


def fetch_active_us_tickers_polygon(max_pages: int = 40, delay: float = 13.0) -> Dict[str, Dict[str, str]]:
    """Fallback universe from Polygon reference tickers (free tier ~5 req/min)."""
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY not set")
    out: Dict[str, Dict[str, str]] = {}
    url = f"{_POLYGON_BASE}?market=stocks&active=true&limit=1000&apiKey={api_key}"
    pages = 0
    while url and pages < max_pages:
        try:
            with urllib.request.urlopen(url, timeout=45) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(delay)
                continue
            raise
        for r in body.get("results", []):
            t = (r.get("ticker") or "").strip().upper()
            if t:
                out.setdefault(t, {
                    "name": (r.get("name") or "").strip()[:200],
                    "asset_type": _TYPE_TO_ASSET.get(r.get("type") or "", "STOCK"),
                    "poly_type": r.get("type") or "",
                })
        pages += 1
        nxt = body.get("next_url")
        url = f"{nxt}&apiKey={api_key}" if nxt else None
        if url:
            time.sleep(delay)
    return out
