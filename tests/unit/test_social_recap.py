"""Weekly recap thread wording and length."""

from datetime import date

import pytest

from domains.social.composer import X_LIMIT, x_length
from domains.social.recap import LateFiler, MemberCount, TickerFlow, WeeklyStats, compose_weekly_thread

pytestmark = pytest.mark.unit


def stats(**kw):
    base = dict(
        start=date(2026, 10, 19), end=date(2026, 10, 25), trades=48, members=9, buys=31, sells=17,
        amount_min_cents=120_000_00, amount_max_cents=3_400_000_00, late_trades=3,
        most_active=[MemberCount(f"Rep. Member Number{i} (R-TX)", 20 - i, 10, 10 - i) for i in range(6)],
        most_bought=[TickerFlow(t, 3, 0, 5) for t in ("NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META")],
        most_sold=[TickerFlow("INTC", 0, 1, 1)],
        late_filers=[LateFiler("Sen. Some Senator (D-CA)", 2, 120)],
    )
    base.update(kw)
    return WeeklyStats(**base)


def test_thread_fits_and_reads_factually():
    lead, replies, link = compose_weekly_thread(stats(), "https://capitolscope.chrislawrence.ca")
    assert lead.startswith("This week in congressional stock trading (Oct 19 to 25):")
    assert "48 trades disclosed by 9 members, $120,000 to $3,400,000 in reported ranges." in lead
    assert "3 disclosed past the 45-day limit." in lead
    assert link in lead
    assert len(replies) == 3
    assert "$NVDA (3 members)" in replies[1] and "$INTC (1 member)" in replies[1]
    assert "up to 120 days after the trade" in replies[2]
    for post in [lead, *replies]:
        assert x_length(post) <= X_LIMIT
        assert "—" not in post


def test_quiet_week_omits_empty_sections():
    lead, replies, _ = compose_weekly_thread(
        stats(trades=1, members=1, late_trades=0, most_bought=[], most_sold=[], late_filers=[]),
        "https://x.test",
    )
    assert "past the 45-day limit" not in lead and "1 trade disclosed by 1 member," in lead
    assert "0 sales" not in lead
    assert len(replies) == 1  # most active only


def test_month_boundary_span():
    lead, _, _ = compose_weekly_thread(stats(start=date(2026, 10, 27), end=date(2026, 11, 2)), "https://x.test")
    assert "(Oct 27 to Nov 2)" in lead
