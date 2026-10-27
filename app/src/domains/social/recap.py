"""
Weekly recap thread for the public X account.

Built from what was DISCLOSED in the window (notification date), not what
was traded, since that is what became public that week. Pure composition
over plain data so the wording is unit-tested; the SQL lives in
``service.collect_weekly_stats``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple

from .composer import X_LIMIT, usd, x_length

DISCLOSURE_LIMIT_DAYS = 45


@dataclass
class MemberCount:
    title: str          # "Rep. Kevin Hern (R-OK)"
    trades: int
    buys: int
    sells: int


@dataclass
class TickerFlow:
    ticker: str
    buyers: int         # distinct members buying
    sellers: int        # distinct members selling
    trades: int


@dataclass
class LateFiler:
    title: str
    late_trades: int
    worst_days: int


@dataclass
class WeeklyStats:
    start: date
    end: date
    trades: int
    members: int
    buys: int
    sells: int
    amount_min_cents: int
    amount_max_cents: int
    late_trades: int
    most_active: List[MemberCount] = field(default_factory=list)
    most_bought: List[TickerFlow] = field(default_factory=list)
    most_sold: List[TickerFlow] = field(default_factory=list)
    late_filers: List[LateFiler] = field(default_factory=list)


def _n(count: int, word: str, plural: str = "") -> str:
    return f"{count} {word if count == 1 else (plural or word + 's')}"


def _mix(buys: int, sells: int) -> str:
    parts = [p for p in (_n(buys, "buy") if buys else "", _n(sells, "sale") if sells else "") if p]
    return ", ".join(parts)


def _span(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start:%b} {start.day} to {end.day}"
    return f"{start:%b} {start.day} to {end:%b} {end.day}"


def _fit(lines: List[str], tail: str = "") -> str:
    """Join lines, dropping from the end until the post fits X's limit."""
    while lines:
        text = "\n".join(lines) + (f"\n\n{tail}" if tail else "")
        if x_length(text) <= X_LIMIT:
            return text
        lines = lines[:-1]
    return tail


def compose_weekly_thread(s: WeeklyStats, base_url: str) -> Tuple[str, List[str], str]:
    """(lead post, replies, link) for the week. Empty replies are omitted."""
    link = f"{base_url.rstrip('/')}/?utm_source=x&utm_medium=social&utm_campaign=weekly"
    lead_lines = [
        f"This week in congressional stock trading ({_span(s.start, s.end)}):",
        "",
        f"{_n(s.trades, 'trade')} disclosed by {_n(s.members, 'member')}, "
        f"{usd(s.amount_min_cents)} to {usd(s.amount_max_cents)} in reported ranges.",
    ]
    if _mix(s.buys, s.sells):
        lead_lines.append(_mix(s.buys, s.sells).capitalize() + ".")
    if s.late_trades:
        lead_lines.append(f"{s.late_trades} disclosed past the {DISCLOSURE_LIMIT_DAYS}-day limit.")
    lead = _fit(lead_lines, link)

    replies: List[str] = []
    if s.most_active:
        lines = ["Most active filers:"] + [
            f"{m.title}: {_n(m.trades, 'trade')}" + (f" ({_mix(m.buys, m.sells)})" if m.buys and m.sells else "")
            for m in s.most_active[:5]
        ]
        replies.append(_fit(lines))
    flows: List[str] = []
    if s.most_bought:
        flows.append("Most bought: " + ", ".join(
            f"${t.ticker} ({t.buyers} member{'s' if t.buyers != 1 else ''})" for t in s.most_bought[:5]
        ))
    if s.most_sold:
        flows.append("Most sold: " + ", ".join(
            f"${t.ticker} ({t.sellers} member{'s' if t.sellers != 1 else ''})" for t in s.most_sold[:5]
        ))
    if flows:
        replies.append(_fit(flows))
    if s.late_filers:
        lines = [f"Filed past the {DISCLOSURE_LIMIT_DAYS}-day limit:"] + [
            f"{f.title}: {_n(f.late_trades, 'trade')}, up to {f.worst_days} days after the trade"
            for f in s.late_filers[:5]
        ]
        replies.append(_fit(lines))
    return lead, [r for r in replies if r], link
