"""
Plain-text formatting shared by the social cards (Pillow) and the share-page
meta tags. Pure functions over plain values, no DB, no Pillow.

Conventions (match the frontend's components/ui/format.ts):
- DB amounts are CENTS.
- The STOCK Act disclosure limit is 45 days; a filing is late when
  notification_date - transaction_date > 45. Amended filings (filing_status
  'A') are never called late.
- Parties are labels only (R/D/I); they are never color-coded.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional
from urllib.parse import urlparse

DISCLOSURE_LIMIT_DAYS = 45
DEFAULT_PUBLIC_BASE_URL = "https://capitolscope.chrislawrence.ca"


def public_base_url() -> str:
    """Absolute site origin used for og:url, og:image and canonical links."""
    return (os.getenv("PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).rstrip("/")


def public_domain() -> str:
    """Domain printed on the cards (defaults to the PUBLIC_BASE_URL host)."""
    explicit = os.getenv("SOCIAL_CARD_DOMAIN")
    if explicit:
        return explicit.strip()
    host = urlparse(public_base_url()).hostname
    return host or "capitolscope.chrislawrence.ca"


# ---------------------------------------------------------------------------
# Plain data carried into the renderers (built by loader.py from the DB).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TradeCardData:
    member_name: str
    chamber: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    ticker: Optional[str] = None
    asset_name: Optional[str] = None
    transaction_type: Optional[str] = None
    amount_min: Optional[int] = None  # cents
    amount_max: Optional[int] = None  # cents
    amount_exact: Optional[int] = None  # cents
    transaction_date: Optional[date] = None
    notification_date: Optional[date] = None
    filing_status: Optional[str] = None


@dataclass(frozen=True)
class MemberCardData:
    name: str
    chamber: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    trade_count: int = 0
    avg_days: Optional[float] = None  # average days to disclose, amendments excluded
    late_count: int = 0  # filings past 45 days, amendments excluded
    last_disclosed: Optional[date] = None


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------
def party_letter(party: Optional[str]) -> Optional[str]:
    key = (party or "").strip().upper()
    if key.startswith("D"):
        return "D"
    if key.startswith("R"):
        return "R"
    if key.startswith("I"):
        return "I"
    return None


def affiliation(party: Optional[str], state: Optional[str], district: Optional[str] = None) -> str:
    """'R-AL' / 'D-NJ-5' style tag; empty string when nothing is known."""
    parts = [party_letter(party), (state or "").strip().upper() or None]
    d = (district or "").strip()
    if d and parts[1]:
        parts.append(d.upper() if not d.isdigit() else str(int(d)))
    return "-".join(p for p in parts if p)


def chamber_title(chamber: Optional[str]) -> Optional[str]:
    c = (chamber or "").strip().lower()
    if c.startswith("sen"):
        return "Sen."
    if c.startswith("house") or c.startswith("rep"):
        return "Rep."
    return None


def chamber_label(chamber: Optional[str]) -> Optional[str]:
    c = (chamber or "").strip().lower()
    if c.startswith("sen"):
        return "U.S. Senate"
    if c.startswith("house") or c.startswith("rep"):
        return "U.S. House"
    return None


def member_display_name(name: str, chamber: Optional[str]) -> str:
    """'Sen. Tommy Tuberville' (title from chamber; none when unknown)."""
    name = " ".join((name or "").split()) or "Unknown member"
    title = chamber_title(chamber)
    return f"{title} {name}" if title else name


def member_line(name: str, chamber: Optional[str], party: Optional[str], state: Optional[str], district: Optional[str] = None) -> str:
    """'Sen. Tommy Tuberville, R-AL'."""
    tag = affiliation(party, state, district if chamber_title(chamber) == "Rep." else None)
    base = member_display_name(name, chamber)
    return f"{base}, {tag}" if tag else base


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------
def trade_verb(transaction_type: Optional[str]) -> str:
    """Stamp text: BOUGHT / SOLD / EXCHANGED / TRADED."""
    t = (transaction_type or "").strip().upper()
    if t.startswith("P"):
        return "BOUGHT"
    if t.startswith("S"):
        return "SOLD"
    if t.startswith("E"):
        return "EXCHANGED"
    return "TRADED"


def usd(cents: int) -> str:
    return f"${round(cents / 100):,}"


def amount_range(amin: Optional[int], amax: Optional[int], exact: Optional[int] = None) -> Optional[str]:
    """'$100,001 to $250,000' from cents; None when no amount is on record."""
    if exact is not None and exact > 0:
        return usd(exact)
    if amin is not None and amax is not None and amax != amin:
        return f"{usd(amin)} to {usd(amax)}"
    if amin is not None and amax is None:
        return f"{usd(amin)}+"
    if amin is not None or amax is not None:
        return usd(amin if amin is not None else amax)  # type: ignore[arg-type]
    return None


def fmt_date(d: Optional[date]) -> Optional[str]:
    """'May 7, 2024'."""
    if d is None:
        return None
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def is_amendment(filing_status: Optional[str]) -> bool:
    return (filing_status or "").strip().upper().startswith("A")


def days_to_disclose(transaction_date: Optional[date], notification_date: Optional[date]) -> Optional[int]:
    if transaction_date is None or notification_date is None:
        return None
    return max(0, (notification_date - transaction_date).days)


def is_late(days: Optional[float], filing_status: Optional[str] = None) -> bool:
    if days is None or is_amendment(filing_status):
        return False
    return days > DISCLOSURE_LIMIT_DAYS


def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def timing_sentence(t: TradeCardData) -> str:
    """The card's footer line and the share description's last sentence."""
    if is_amendment(t.filing_status):
        return "Amended filing."
    days = days_to_disclose(t.transaction_date, t.notification_date)
    if days is None:
        return "Disclosure date not on record."
    if days > DISCLOSURE_LIMIT_DAYS:
        return f"{plural(days, 'day')} to disclose. Limit: {DISCLOSURE_LIMIT_DAYS}."
    if days == 0:
        return f"Disclosed the same day. Limit: {DISCLOSURE_LIMIT_DAYS}."
    return f"Disclosed in {plural(days, 'day')}. Limit: {DISCLOSURE_LIMIT_DAYS}."


_TICKER_SUFFIX = re.compile(r"\s*\(([A-Z0-9.\-/]{1,10})\)\s*$")
_COMMON_SUFFIX = re.compile(
    r"\s*[-,]?\s*(common stock|common shares|ordinary shares|class [a-z] common stock|common)\s*$",
    re.IGNORECASE,
)


def clean_asset_name(name: Optional[str]) -> Optional[str]:
    """Trim disclosure noise: trailing '(TICKER)', '- Common Stock', dangling punctuation."""
    if not name:
        return None
    s = " ".join(str(name).split())
    s = _TICKER_SUFFIX.sub("", s)
    s = _COMMON_SUFFIX.sub("", s)
    s = s.strip(" -,;:")
    s = re.sub(r"(?:\s+\.|\s*\.\s*-)\s*$", "", s).strip(" -,;:")  # dangling " ." / ". -" from parsing
    return s or None


def short_asset_label(name: Optional[str], max_words: int = 3) -> str:
    """Headline stand-in for assets with no ticker: 'TREASURY BILL'."""
    s = clean_asset_name(name) or "Undisclosed asset"
    s = re.split(r"[(\[,;:]", s, maxsplit=1)[0].strip() or s
    words = s.split()
    return " ".join(words[:max_words]).upper()


def trade_headline(t: TradeCardData) -> str:
    """'Sen. Tommy Tuberville (R-AL) bought INTC'."""
    tag = affiliation(t.party, t.state)
    who = member_display_name(t.member_name, t.chamber) + (f" ({tag})" if tag else "")
    what = t.ticker or clean_asset_name(t.asset_name) or "an asset"
    verb = {"BOUGHT": "bought", "SOLD": "sold", "EXCHANGED": "exchanged"}.get(trade_verb(t.transaction_type), "traded")
    return f"{who} {verb} {what}"


def trade_description(t: TradeCardData) -> str:
    """One or two factual sentences for meta descriptions."""
    verb = trade_verb(t.transaction_type).capitalize()
    amount = amount_range(t.amount_min, t.amount_max, t.amount_exact)
    name = clean_asset_name(t.asset_name)
    asset = name or t.ticker or "an asset"
    if t.ticker and name:
        asset = f"{name} ({t.ticker})"
    parts = [verb]
    if amount:
        parts.append(amount)
        parts.append("of")
    parts.append(asset)
    traded = fmt_date(t.transaction_date)
    if traded:
        parts.append(f"on {traded}")
    first = " ".join(parts) + "."
    disclosed = fmt_date(t.notification_date)
    second = f"Disclosed {disclosed}. " if disclosed else ""
    return f"{first} {second}{timing_sentence(t)}".strip()


def member_description(m: MemberCardData) -> str:
    if m.trade_count <= 0:
        return "No stock trade disclosures on record."
    bits = [f"{plural(m.trade_count, 'disclosed trade')}."]
    if m.avg_days is not None:
        bits.append(f"Average {round(m.avg_days):,} days to disclose.")
    bits.append(
        f"{plural(m.late_count, 'filing')} past the {DISCLOSURE_LIMIT_DAYS}-day limit."
        if m.late_count
        else f"No filings past the {DISCLOSURE_LIMIT_DAYS}-day limit."
    )
    return " ".join(bits)
