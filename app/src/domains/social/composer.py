"""
Post text for the public X account.

Deterministic templates filled from database fields: no model writes facts.
Tone is neutral and factual. Members are not @-mentioned (automated
mentions trip X's spam rules). X counts every URL as 23 characters.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from .selector import DISCLOSURE_LIMIT_DAYS, Candidate, TradeFacts, total_range

X_LIMIT = 280
X_URL_LENGTH = 23

_VERB = {"P": "a purchase of", "S": "a sale of", "E": "an exchange of"}
_OWNER = {"SP": " by a spouse", "JT": " held jointly", "DC": " by a dependent child"}


def x_length(text: str) -> int:
    """Length as X counts it: each http(s) URL counts as 23 characters."""
    total = 0
    for word in text.split(" "):
        for i, part in enumerate(word.split("\n")):
            if i:
                total += 1  # the newline itself
            total += X_URL_LENGTH if part.startswith(("http://", "https://")) else len(part)
    return total + text.count(" ")


def usd(cents: int) -> str:
    return f"${round(cents / 100):,}"


def amount_range(amin: int | None, amax: int | None) -> str:
    if amin is not None and amax is not None and amax != amin:
        return f"{usd(amin)} to {usd(amax)}"
    if amin is not None and amax is None:
        return f"over {usd(amin)}"
    return usd(amin if amin is not None else amax or 0)


def fmt_date(d: date, today: date) -> str:
    return d.strftime("%b %-d") if d.year == today.year else d.strftime("%b %-d, %Y")


def title(t: TradeFacts) -> str:
    chamber = (t.chamber or "").lower()
    prefix = "Sen." if chamber.startswith("s") else "Rep." if chamber.startswith("h") else ""
    aff = "-".join(p for p in ((t.party or "")[:1].upper() or None, t.state) if p)
    return f"{prefix} {t.member_name}{f' ({aff})' if aff else ''}".strip()


def clean_name(name: Optional[str], ticker: Optional[str]) -> str:
    """A short, trustworthy company name for parentheses, or '' to omit it."""
    name = re.sub(r"\s+", " ", (name or "")).strip(" ,.")
    if not name or (ticker and name.upper() == ticker.upper()):
        return ""
    if len(re.findall(r"[A-Za-z]", name)) < 3 or re.search(r"[:;|]|description", name, re.I):
        return ""
    for _ in range(3):  # trim legal suffixes like ", Inc." / "Corporation"
        trimmed = re.sub(r"[,\s]+(inc|corp|corporation|plc|ltd|co|company|common stock|class [a-z])\.?$", "", name, flags=re.I).strip(" ,.")
        if trimmed == name:
            break
        name = trimmed
    if ticker and name.upper() == ticker.upper():
        return ""
    return name if 2 < len(name) <= 32 else ""


def asset(t: TradeFacts) -> str:
    if t.ticker:
        # Prefer the matched security's name: parsed asset text is often garbled.
        short = clean_name(t.security_name, t.ticker) if t.security_name else clean_name(t.asset_name, t.ticker)
        return f"${t.ticker}{f' ({short})' if short else ''}"
    return (t.asset_name or "an undisclosed asset").strip()[:60]


def timing_line(t: TradeFacts, today: date) -> str:
    days = t.days_to_disclose
    traded, filed = fmt_date(t.transaction_date, today), fmt_date(t.notification_date, today)
    if days > DISCLOSURE_LIMIT_DAYS:
        return f"Traded {traded}, disclosed {filed}: {days} days, past the {DISCLOSURE_LIMIT_DAYS}-day limit."
    if days == 0:
        return f"Traded and disclosed {filed}."
    return f"Traded {traded}, disclosed {filed} ({days} days)."


def compose_trade(t: TradeFacts, url: str, today: date) -> str:
    owner = _OWNER.get((t.owner or "").upper(), "")
    verb = _VERB.get(t.transaction_type.upper()[:1], "a trade in")
    lead = f"{title(t)} disclosed {verb} {asset(t)}{owner}, {amount_range(t.amount_min, t.amount_max)}."
    text = f"{lead}\n\n{timing_line(t, today)}\n\n{url}"
    if x_length(text) > X_LIMIT:  # drop the company name in parentheses first
        lead = f"{title(t)} disclosed {verb} ${t.ticker}{owner}, {amount_range(t.amount_min, t.amount_max)}." if t.ticker else lead[:150]
        text = f"{lead}\n\n{timing_line(t, today)}\n\n{url}"
    return text


def compose_rollup(trades: List[TradeFacts], url: str, today: date) -> str:
    lead_t = trades[0]  # largest first (selector sorts by amount)
    lo, hi = total_range(trades)
    buys = sum(1 for t in trades if t.transaction_type.upper().startswith("P"))
    sells = sum(1 for t in trades if t.transaction_type.upper().startswith("S"))
    exchanges = len(trades) - buys - sells
    mix = ", ".join(
        p
        for p in (
            f"{buys} buys" if buys else "",
            f"{sells} sales" if sells else "",
            f"{exchanges} exchange{'s' if exchanges != 1 else ''}" if exchanges else "",
        )
        if p
    )
    late = sum(1 for t in trades if t.is_late)
    lines = [
        f"{title(lead_t)} disclosed {len(trades)} trades in one filing ({mix}), "
        f"{usd(lo)} to {usd(hi)} in reported ranges.",
        f"Largest: {_VERB.get(lead_t.transaction_type.upper()[:1], 'a trade in')} {asset(lead_t)}, "
        f"{amount_range(lead_t.amount_min, lead_t.amount_max)}.",
    ]
    if late:
        lines.append(f"{late} of them disclosed past the {DISCLOSURE_LIMIT_DAYS}-day limit.")
    text = "\n\n".join(lines) + f"\n\n{url}"
    if x_length(text) > X_LIMIT:
        text = "\n\n".join(lines[:1] + lines[2:]) + f"\n\n{url}"
    return text


def compose(candidate: Candidate, base_url: str, today: date) -> tuple[str, str]:
    """(post text, link url) for a candidate."""
    base = base_url.rstrip("/")
    utm = "utm_source=x&utm_medium=social"
    if candidate.kind == "rollup":
        url = f"{base}/members/{candidate.lead.member_id}?{utm}"
        return compose_rollup(candidate.trades, url, today), url
    url = f"{base}/t/{candidate.lead.trade_id}?{utm}"
    return compose_trade(candidate.lead, url, today), url
