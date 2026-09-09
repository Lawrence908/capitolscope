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
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
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
# Polygon ``type`` codes worth keeping in the cached universe. Excludes
# warrants, units, rights, and structured products the disclosures don't name.
_KEEP_POLY_TYPES = {
    "CS", "ADRC", "ADRP", "ETF", "ETN", "ETV", "FUND", "PFD", "REIT", "ETS",
}

# Types usable for *matching* a delisted symbol (PFD dropped: a preferred listing
# must not shadow a renamed common). Active symbols are always matchable.
_MATCHABLE_DELISTED_TYPES = {
    "CS", "ADRC", "ADRP", "ETF", "ETN", "ETV", "FUND", "REIT", "ETS",
}
# Electronic PTR disclosures start ~2012; a symbol delisted before this era is
# almost never what a trade references, and old records carry noisy metadata and
# reused tickers. Bound delisted matching to the disclosure era.
_PTR_ERA_MIN_YEAR = os.environ.get("CAPITOLSCOPE_UNIVERSE_MIN_DELIST_YEAR", "2011")

# Disk cache so the (large) delisted-inclusive universe is fetched at most once
# per TTL instead of on every backfill/ingestion run.
_CACHE_PATH = os.environ.get(
    "CAPITOLSCOPE_UNIVERSE_CACHE",
    os.path.join(tempfile.gettempdir(), "capitolscope_universe.json"),
)
_CACHE_TTL_DAYS = float(os.environ.get("CAPITOLSCOPE_UNIVERSE_CACHE_TTL_DAYS", "7"))


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


def _polygon_page(url: str, retries: int = 6, backoff: float = 12.0) -> dict:
    """One Polygon request with 429 backoff (paid keys rarely need it)."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=45) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(backoff)
                continue
            raise
        except Exception:  # transient network blip
            if attempt == retries - 1:
                raise
            time.sleep(3.0)
    raise RuntimeError("Polygon paging: retries exhausted")


# OTC market: only foreign ADRs are worth ingesting (Roche, LVMH, Tencent,
# Nestle, ...). Domestic pink-sheet "CS"/"OS" shells add far more name-collision
# noise than recall, so they are excluded.
_OTC_KEEP_TYPES = {"ADRC", "ADRP"}


def _page_market(api_key: str, market: str, active: str, keep_types: set,
                 out: Dict[str, Dict[str, str]], max_pages: int) -> None:
    """Page one Polygon market/active-state into ``out`` (active wins ties)."""
    url = f"{_POLYGON_BASE}?market={market}&active={active}&limit=1000&apiKey={api_key}"
    pages = 0
    while url and pages < max_pages:
        body = _polygon_page(url)
        pages += 1
        for r in body.get("results", []):
            sym = (r.get("ticker") or "").strip().upper()
            poly_type = r.get("type") or ""
            if not sym or any(c in sym for c in "$^ "):  # warrants/units/junk
                continue
            if poly_type and poly_type not in keep_types:
                continue
            rec = {
                "name": (r.get("name") or "").strip()[:200],
                "asset_type": _TYPE_TO_ASSET.get(poly_type, "STOCK"),
                "active": active == "true",
                "delisted_utc": r.get("delisted_utc"),
                "poly_type": poly_type,
                "otc": market == "otc",
            }
            existing = out.get(sym)
            # Active wins over delisted; otherwise keep the first seen.
            if existing is None or (rec["active"] and not existing.get("active")):
                out[sym] = rec
        nxt = body.get("next_url")
        url = f"{nxt}&apiKey={api_key}" if nxt else None


def fetch_us_universe_polygon(
    include_delisted: bool = True, include_otc: bool = True, max_pages: int = 120
) -> Dict[str, Dict[str, str]]:
    """Full US securities universe from Polygon: listed active + (optionally)
    delisted, plus (optionally) OTC foreign ADRs.

    Delisted symbols let historical trades (Twitter, Celgene, United
    Technologies, ...) resolve; OTC ADRs cover foreign names (Roche, LVMH,
    Tencent) that never had a US listing. Active entries win ties over delisted
    ones with the same symbol (tickers get reused). Returns
    ``{TICKER: {"name", "asset_type", "active", "delisted_utc", "poly_type", "otc"}}``.
    """
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY not set")

    out: Dict[str, Dict[str, str]] = {}
    for active in (["true", "false"] if include_delisted else ["true"]):
        _page_market(api_key, "stocks", active, _KEEP_POLY_TYPES, out, max_pages)
    if include_otc:
        for active in (["true", "false"] if include_delisted else ["true"]):
            _page_market(api_key, "otc", active, _OTC_KEEP_TYPES, out, max_pages)

    active_n = sum(1 for v in out.values() if v.get("active"))
    otc_n = sum(1 for v in out.values() if v.get("otc"))
    logger.info(
        "Polygon universe: %d symbols (%d active, %d delisted, %d OTC ADR)",
        len(out), active_n, len(out) - active_n, otc_n,
    )
    if len(out) < 5000:
        raise RuntimeError(f"Polygon universe suspiciously small ({len(out)}); refusing to use")
    return out


def select_matchable(universe_meta: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Restrict a raw universe to symbols safe to match congressional trades against.

    Keeps every active symbol; keeps a delisted symbol only if it is a common /
    ADR / ETF (not preferred) *and* was delisted in the PTR era (>= 2011). This
    is what removes reused-ticker collisions (Monsanto's MON is now a 2022 SPAC)
    and pre-modern-metadata junk (a 2007 warrant record) without dropping the
    genuine historical names (Twitter, Celgene, United Technologies).
    """
    out: Dict[str, Dict[str, str]] = {}
    for sym, meta in universe_meta.items():
        if meta.get("active", True):
            out[sym] = meta
            continue
        poly_type = meta.get("poly_type") or meta.get("asset_type") or ""
        if poly_type not in _MATCHABLE_DELISTED_TYPES:
            continue
        delist_year = (meta.get("delisted_utc") or "")[:4]
        if delist_year and delist_year >= _PTR_ERA_MIN_YEAR:
            out[sym] = meta
    return out


def _cache_fresh(path: str, ttl_days: float) -> bool:
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return age < ttl_days * 86400


def load_universe(include_delisted: bool = True, refresh: bool = False) -> Dict[str, Dict[str, str]]:
    """Return the securities universe used for validation and name matching.

    Prefers Polygon (active + delisted) with a TTL disk cache; falls back to the
    Nasdaq Trader active-only feed when no Polygon key is configured or Polygon
    fails. The cache makes repeated backfill/ingestion runs cheap and gives
    offline resilience. Shape matches :func:`fetch_us_universe_polygon`.
    """
    if not refresh and _cache_fresh(_CACHE_PATH, _CACHE_TTL_DAYS):
        try:
            with open(_CACHE_PATH) as fh:
                data = json.load(fh)
            if data:
                logger.info("Loaded universe from cache: %d symbols (%s)", len(data), _CACHE_PATH)
                return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Universe cache unreadable (%s); refetching", exc)

    universe: Dict[str, Dict[str, str]] = {}
    if os.environ.get("POLYGON_API_KEY"):
        try:
            universe = fetch_us_universe_polygon(include_delisted=include_delisted)
        except Exception as exc:
            logger.warning("Polygon universe fetch failed (%s); falling back to Nasdaq Trader", exc)

    if not universe:
        # Nasdaq feed has no active flag; treat all as active.
        for sym, meta in fetch_active_us_tickers().items():
            universe[sym] = {**meta, "active": True, "delisted_utc": None}
    else:
        # Supplement with any active Nasdaq symbol Polygon type-filtered out.
        try:
            for sym, meta in fetch_active_us_tickers().items():
                universe.setdefault(sym, {**meta, "active": True, "delisted_utc": None})
        except Exception as exc:
            logger.debug("Nasdaq supplement skipped: %s", exc)

    try:
        tmp = f"{_CACHE_PATH}.tmp"
        with open(tmp, "w") as fh:
            json.dump(universe, fh)
        os.replace(tmp, _CACHE_PATH)
        logger.info("Wrote universe cache: %d symbols -> %s", len(universe), _CACHE_PATH)
    except OSError as exc:
        logger.warning("Could not write universe cache (%s)", exc)

    return universe
