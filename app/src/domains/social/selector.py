"""
Which newly disclosed trades are worth posting.

Pure functions over plain dataclasses (no DB) so the policy is unit-tested.
Precision over volume: a public account that posts a wrong "late filing"
claim loses its credibility, so anything uncertain is filtered out.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Set

DISCLOSURE_LIMIT_DAYS = 45

# Amounts are stored in CENTS.
CENTS = 100
SINGLE_POST_MIN_CENTS = 250_001 * CENTS   # always worth a post on size alone
NOTABLE_SCORE = 40                        # otherwise post when the score reaches this
ROLLUP_MIN_TRADES = 5                     # one filing with this many trades gets a roll-up
MIN_TICKER_CONFIDENCE = 0.7


@dataclass(frozen=True)
class TradeFacts:
    trade_id: str
    member_id: str
    member_name: str
    party: Optional[str]
    state: Optional[str]
    chamber: Optional[str]
    district: Optional[str]
    doc_id: str
    ticker: Optional[str]
    asset_name: Optional[str]
    transaction_type: str
    transaction_date: date
    notification_date: date
    amount_min: Optional[int]
    amount_max: Optional[int]
    owner: Optional[str] = None
    filing_status: Optional[str] = None
    parsed_successfully: Optional[bool] = True
    ticker_confidence: Optional[float] = None
    sector: Optional[str] = None
    security_name: Optional[str] = None  # name of the matched security (cleaner than parsed asset text)
    committee_sectors: frozenset = field(default_factory=frozenset)
    leadership: bool = False

    @property
    def days_to_disclose(self) -> int:
        return max(0, (self.notification_date - self.transaction_date).days)

    @property
    def is_late(self) -> bool:
        return not self.is_amendment and self.days_to_disclose > DISCLOSURE_LIMIT_DAYS

    @property
    def is_amendment(self) -> bool:
        return (self.filing_status or "").upper().startswith("A")

    @property
    def committee_overlap(self) -> bool:
        return bool(self.sector) and self.sector in self.committee_sectors


@dataclass
class Candidate:
    kind: str  # "trade" | "rollup"
    trades: List[TradeFacts]
    score: int
    reasons: List[str]

    @property
    def lead(self) -> TradeFacts:
        return self.trades[0]


def eligible(t: TradeFacts, today: date) -> Optional[str]:
    """None if the trade may be posted, else the reason it is excluded."""
    if t.is_amendment:
        return "amended filing"
    if t.parsed_successfully is False:
        return "not parsed cleanly"
    if t.transaction_date > today or t.notification_date > today:
        return "future-dated"
    if t.transaction_date > t.notification_date:
        return "traded after filing date"
    # v1 posts only exchange-listed securities with a ticker: free-text assets
    # (private holdings, bonds, "XXX" placeholders) parse too unreliably.
    if not t.ticker:
        return "no ticker"
    if not (t.party and t.chamber):
        return "member identity incomplete"
    if t.ticker and t.ticker_confidence is not None and t.ticker_confidence < MIN_TICKER_CONFIDENCE:
        return "low ticker confidence"
    if t.amount_min is None and t.amount_max is None:
        return "no amount"
    if not t.member_name:
        return "no member"
    return None


def score_trade(t: TradeFacts) -> tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    amin = t.amount_min or 0
    for floor_dollars, points in ((1_000_001, 50), (500_001, 40), (250_001, 30), (100_001, 20), (50_001, 10)):
        if amin >= floor_dollars * CENTS:
            score += points
            reasons.append(f"size: ${floor_dollars:,}+")
            break
    if t.is_late:
        late_by = t.days_to_disclose - DISCLOSURE_LIMIT_DAYS
        score += 25 + (10 if late_by > 45 else 0)
        reasons.append(f"late: {t.days_to_disclose} days to disclose")
    if t.committee_overlap:
        score += 20
        reasons.append(f"committee overlap: {t.sector}")
    if t.leadership:
        score += 10
        reasons.append("leadership role")
    return score, reasons


def select_candidates(
    trades: Iterable[TradeFacts],
    today: date,
    already_posted: Optional[Set[str]] = None,
) -> List[Candidate]:
    """Rank new trades into post candidates.

    - A single-trade post for every eligible trade of $250,001+ or scoring
      NOTABLE_SCORE or more.
    - One roll-up per filing (doc_id) with ROLLUP_MIN_TRADES+ eligible trades,
      covering the trades not already given a single post.
    """
    already_posted = already_posted or set()
    pool = [t for t in trades if t.trade_id not in already_posted and eligible(t, today) is None]

    singles: List[Candidate] = []
    single_ids: Set[str] = set()
    for t in pool:
        score, reasons = score_trade(t)
        if (t.amount_min or 0) >= SINGLE_POST_MIN_CENTS or score >= NOTABLE_SCORE:
            singles.append(Candidate("trade", [t], score, reasons))
            single_ids.add(t.trade_id)

    by_filing: Dict[str, List[TradeFacts]] = defaultdict(list)
    for t in pool:
        by_filing[t.doc_id].append(t)
    rollups: List[Candidate] = []
    for doc_trades in by_filing.values():
        if len(doc_trades) < ROLLUP_MIN_TRADES:
            continue
        rest = [t for t in doc_trades if t.trade_id not in single_ids]
        if len(rest) < ROLLUP_MIN_TRADES:
            continue
        rest.sort(key=lambda t: (t.amount_min or 0), reverse=True)
        score = 15 + min(25, len(rest))
        reasons = [f"filing with {len(rest)} trades"]
        if any(t.is_late for t in rest):
            score += 15
            reasons.append("includes late trades")
        rollups.append(Candidate("rollup", rest, score, reasons))

    out = singles + rollups
    out.sort(key=lambda c: c.score, reverse=True)
    return out


def total_range(trades: Sequence[TradeFacts]) -> tuple[int, int]:
    """Sum of reported ranges in cents (min, max), using min for open-ended ranges."""
    lo = sum(t.amount_min or 0 for t in trades)
    hi = sum((t.amount_max if t.amount_max is not None else (t.amount_min or 0)) for t in trades)
    return lo, hi
