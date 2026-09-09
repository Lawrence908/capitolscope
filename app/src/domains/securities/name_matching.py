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
from typing import Dict, List, Optional, Tuple

# Legal-form / boilerplate tokens stripped from the end (or anywhere) of a name
# so both sides normalize identically.
_SUFFIX_TOKENS = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "companies",
    "ltd", "limited", "plc", "llc", "lp", "llp", "sa", "nv", "ag", "se",
    "trust", "the",
    # Foreign legal forms the disclosure text carries but the listing name may
    # not (or vice versa): "Eaton ... plc", "Bayer Aktiengesellschaft".
    "aktiengesellschaft", "oyj", "asa", "spa", "kgaa",
    # Share-class / instrument words that appear un-paired ("Hershey Common",
    # "Accenture Ordinary", "Antero Midstream Partners Common Units", "Nestle
    # Sponsored ADS"). Their paired phrases ("common stock", "ordinary shares")
    # are also handled in _BOILERPLATE.
    "common", "ordinary", "share", "stock", "unit", "units", "sponsored", "ads",
    # Fund/ETF boilerplate — lets "SPDR Gold Trust" match "SPDR Gold Shares",
    # "X ETF" match "X", etc. Verified net-positive with no stock regression.
    "etf", "fund", "index", "shares",
}
_BOILERPLATE = [
    "common stock", "ordinary shares", "class a", "class b", "class c",
    "depositary shares", "american depositary", "adr", "reit",
]
# Dotted foreign legal forms ("Schlumberger N.V", "Banco Santander S.A") that
# survive as stray single-letter tokens ("n v", "s a") after punctuation
# stripping. Removed only at the END of the name so interior words are safe.
_DOTTED_SUFFIX_RE = re.compile(
    r"\b(?:"
    r"n\.?\s*v|s\.?\s*a\.?\s*b?(?:\.?\s*de\s*c\.?\s*v)?|s\.?\s*p\.?\s*a|"
    r"p\.?\s*l\.?\s*c|a\.?\s*g|a\.?\s*b|a\.?\s*s|s\.?\s*e|k\.?\s*k"
    r")\.?\s*$"
)
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")
# ADR "…each representing N ordinary shares" tails carry no identity; cut them.
_ADR_REPRESENT_RE = re.compile(r"\b(each\s+representing|representing)\b.*$", re.I)
# Trailing ADR/instrument descriptor tokens popped only from the END of the name
# ("Komatsu Ord American" -> "komatsu"). Not stripped mid-name, so "American
# Express" / "Bank of America" are untouched.
_TRAILING_DESC = {
    "american", "unsponsored", "ord", "new", "spon", "cptl", "shs", "adr",
}


def normalize_company_name(name: Optional[str]) -> str:
    """Normalize a company name to a comparable key ('' if nothing usable)."""
    if not name:
        return ""
    s = name.lower()
    s = s.replace("&", " and ")
    s = _ADR_REPRESENT_RE.sub(" ", s)
    for phrase in _BOILERPLATE:
        s = s.replace(phrase, " ")
    s = _DOTTED_SUFFIX_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    tokens = [t for t in _WS_RE.sub(" ", s).strip().split(" ") if t and t not in _SUFFIX_TOKENS]
    while tokens and tokens[-1] in _TRAILING_DESC:
        tokens.pop()
    return " ".join(tokens)


def _pick_preferred(members: List[Tuple[str, Dict[str, str]]]) -> Optional[str]:
    """Choose a single ticker among symbols that share a normalized name.

    Preference: active over delisted, then a "plain" symbol (all letters, no
    class suffix like ``.A``/``-B``) over a suffixed one, then the shortest.
    Only returns a symbol when the top candidate is *strictly* better than the
    runner-up on that (active, plain, length) key; a genuine tie stays ambiguous
    and is dropped, because a wrong ``security_id`` corrupts every downstream
    join. ``active`` defaults to True when the metadata omits it (Nasdaq feed).
    """
    def sort_key(item: Tuple[str, Dict[str, str]]):
        symbol, meta = item
        active = 0 if meta.get("active", True) else 1          # active first
        plain = 0 if re.fullmatch(r"[A-Z]+", symbol) else 1     # plain first
        return (active, plain, len(symbol), symbol)

    ranked = sorted(members, key=sort_key)
    if len(ranked) == 1:
        return ranked[0][0]
    # Strictly better than the runner-up on (active, plain, length)?
    if sort_key(ranked[0])[:3] < sort_key(ranked[1])[:3]:
        return ranked[0][0]
    return None


def build_name_index(universe_meta: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """normalized name -> ticker.

    Symbols sharing a normalized name are resolved by :func:`_pick_preferred`
    (active/plain/shortest); unresolved ties are dropped for precision.
    """
    groups: Dict[str, List[Tuple[str, Dict[str, str]]]] = {}
    for symbol, meta in universe_meta.items():
        key = normalize_company_name(meta.get("name"))
        if not key:
            continue
        groups.setdefault(key, []).append((symbol.strip().upper(), meta))
    index: Dict[str, str] = {}
    for key, members in groups.items():
        symbol = _pick_preferred(members)
        if symbol:
            index[key] = symbol
    return index


def resolve_ticker_by_name(raw_asset: Optional[str], name_index: Dict[str, str]) -> Optional[str]:
    """Resolve a ticker from an asset description via exact normalized-name match."""
    key = normalize_company_name(raw_asset)
    if not key:
        return None
    return name_index.get(key)


# ---------------------------------------------------------------------------
# Fixed-income / non-common-equity guards.
#
# Disclosures include bonds, notes, treasuries, municipals, and preferred/
# depositary instruments. Equity name-matching must not (a) match a bond/note to
# its issuer's *stock* (wrong instrument) nor (b) let a preferred/depositary
# listing shadow the common when the common was renamed. Both are precision
# losses that silently corrupt returns.
# ---------------------------------------------------------------------------
_FIXED_INCOME_RE = re.compile(
    r"\b(notes?|bonds?|sr nt|coupon|debenture|treasur\w*|muni\w*|municipal|"
    r"rev rfdg|rfdg|revenue|dorm auth|authority|maturity|matures|"
    r"due \d|series \d{4}|certificate of deposit)\b",
    re.I,
)
_COUPON_RE = re.compile(r"\d+(?:\.\d+)?\s*%")

# Names that are not plain common/ADR equity (preferred, notes, depositary
# *preferred*, warrants, rights, units); excluded as name-match targets.
_NONCOMMON_NAME_RE = re.compile(
    r"\b(notes?|coupon|due \d|mandatory|preferred|pfd|debenture|warrant|"
    r"rights?|series [a-z]\b)\b",
    re.I,
)


def looks_like_fixed_income(raw_asset: Optional[str]) -> bool:
    """True if the disclosure text is a bond/note/treasury/municipal/CD rather
    than an equity (so it should never be matched to a stock ticker)."""
    if not raw_asset:
        return False
    if _FIXED_INCOME_RE.search(raw_asset):
        return True
    return bool(_COUPON_RE.search(raw_asset))


def is_common_equity_target(meta: Dict[str, str]) -> bool:
    """True if a universe entry is a plain common/ADR/ETF listing usable as a
    name-match target (excludes preferred stock and fixed-income listings)."""
    if (meta.get("poly_type") or meta.get("asset_type")) == "PFD":
        return False
    return not _NONCOMMON_NAME_RE.search(meta.get("name") or "")


def build_containment_index(name_index: Dict[str, str]) -> Dict[str, object]:
    """Build an inverted token index over ``name_index`` keys for containment
    matching. Returned bundle is opaque input to :func:`resolve_ticker_by_containment`."""
    inverted: Dict[str, list] = {}
    key_tokens: Dict[str, set] = {}
    for key in name_index:
        tokens = set(key.split())
        key_tokens[key] = tokens
        for tok in tokens:
            inverted.setdefault(tok, []).append(key)
    doc_freq = {tok: len(keys) for tok, keys in inverted.items()}
    return {"inverted": inverted, "key_tokens": key_tokens, "doc_freq": doc_freq}


def resolve_ticker_by_containment(
    raw_asset: Optional[str],
    name_index: Dict[str, str],
    containment_index: Dict[str, object],
    *,
    max_token_df: int = 3000,
) -> Optional[str]:
    """Resolve a ticker when the disclosure name is a token sub/superset of
    exactly one listing name.

    Handles verbose or lightly-renamed listing names ("Taiwan Semiconductor" vs
    "Taiwan Semiconductor Manufacturing Company", "Cigna" vs "The Cigna Group",
    "Crown Castle International" vs "Crown Castle"). Precision guards:

      * fixed-income / coupon descriptions are skipped;
      * the *subset* direction (query ⊆ listing) is always allowed — the query
        is the more specific string;
      * the *superset* direction (listing ⊂ query) requires the listing name to
        have ≥2 tokens, so a one-word listing ("Atlas") can't swallow an
        unrelated longer name ("Atlas Copco");
      * a match is returned only when a single ticker qualifies, or one ticker's
        name is a strictly tighter (smaller) superset than any other.
    """
    if looks_like_fixed_income(raw_asset):
        return None
    query = normalize_company_name(raw_asset)
    if not query or len(query) < 4:
        return None
    q_tokens = set(query.split())
    if not q_tokens:
        return None

    inverted = containment_index["inverted"]
    key_tokens = containment_index["key_tokens"]
    doc_freq = containment_index["doc_freq"]

    # Seed candidates from the rarest query token; skip if even that is too common
    # (a bare "energy"/"group" query shouldn't fan out across the whole market).
    rarest = min(q_tokens, key=lambda t: doc_freq.get(t, 1 << 30))
    if doc_freq.get(rarest, 0) > max_token_df:
        return None

    # ticker -> smallest listing-name token count that contained/was-contained-by
    best_size: Dict[str, int] = {}
    for key in inverted.get(rarest, []):
        k_tokens = key_tokens[key]
        if q_tokens.issubset(k_tokens):            # query more specific: safe
            ok = True
        elif k_tokens.issubset(q_tokens) and len(k_tokens) >= 2:  # listing subset
            ok = True
        else:
            ok = False
        if ok:
            ticker = name_index[key]
            best_size[ticker] = min(best_size.get(ticker, 1 << 30), len(k_tokens))

    if not best_size:
        return None
    if len(best_size) == 1:
        return next(iter(best_size))
    # Multiple tickers: accept only a unique tightest (smallest-superset) name.
    ranked = sorted(best_size.items(), key=lambda kv: kv[1])
    if ranked[0][1] < ranked[1][1]:
        return ranked[0][0]
    return None
