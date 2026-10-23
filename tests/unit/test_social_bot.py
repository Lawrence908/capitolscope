"""X bot policy: which trades get posted and what the posts say."""

from datetime import date, datetime, timezone

import pytest

from domains.social.composer import X_LIMIT, amount_range, clean_name, compose, x_length
from domains.social.selector import TradeFacts, eligible, score_trade, select_candidates
from domains.social.service import in_window

pytestmark = pytest.mark.unit

TODAY = date(2026, 10, 23)
BASE = "https://capitolscope.chrislawrence.ca"


def trade(i=1, **kw) -> TradeFacts:
    base = dict(
        trade_id=f"t{i}",
        member_id="m1",
        member_name="Tommy Tuberville",
        party="R",
        state="AL",
        chamber="Senate",
        district=None,
        doc_id="doc1",
        ticker="INTC",
        asset_name="Intel Corporation",
        transaction_type="P",
        transaction_date=date(2026, 9, 1),
        notification_date=date(2026, 10, 20),
        amount_min=100_001_00,
        amount_max=250_000_00,
    )
    base.update(kw)
    return TradeFacts(**base)


class TestEligibility:
    def test_amendments_never_posted(self):
        assert eligible(trade(filing_status="A"), TODAY) == "amended filing"

    def test_future_dated_skipped(self):
        assert eligible(trade(transaction_date=date(2026, 12, 26)), TODAY) == "future-dated"

    def test_low_ticker_confidence_skipped(self):
        assert eligible(trade(ticker_confidence=0.4), TODAY) == "low ticker confidence"

    def test_unparsed_skipped(self):
        assert eligible(trade(parsed_successfully=False), TODAY) == "not parsed cleanly"

    def test_no_ticker_skipped(self):
        assert eligible(trade(ticker=None, asset_name="XXX"), TODAY) == "no ticker"

    def test_unknown_member_identity_skipped(self):
        assert eligible(trade(party=None, chamber=None, member_name="Conley II"), TODAY) == "member identity incomplete"

    def test_clean_trade_ok(self):
        assert eligible(trade(), TODAY) is None


class TestScoring:
    def test_amounts_are_cents(self):
        # $1,001 to $15,000 is small: no size points
        score, _ = score_trade(trade(amount_min=1_001_00, amount_max=15_000_00, notification_date=date(2026, 9, 5)))
        assert score == 0

    def test_late_and_large(self):
        score, reasons = score_trade(trade(amount_min=500_001_00, amount_max=1_000_000_00))
        assert score >= 40 + 25
        assert any(r.startswith("late:") for r in reasons)

    def test_amendment_not_late(self):
        assert not trade(filing_status="A", transaction_date=date(2024, 5, 7)).is_late

    def test_committee_overlap(self):
        t = trade(sector="Information Technology", committee_sectors=frozenset({"Information Technology"}))
        _, reasons = score_trade(t)
        assert "committee overlap: Information Technology" in reasons


class TestSelection:
    def test_large_trade_gets_single_post(self):
        c = select_candidates([trade(amount_min=250_001_00, amount_max=500_000_00, notification_date=date(2026, 9, 5))], TODAY)
        assert [x.kind for x in c] == ["trade"]

    def test_small_on_time_trade_ignored(self):
        assert select_candidates([trade(amount_min=1_001_00, amount_max=15_000_00, notification_date=date(2026, 9, 5))], TODAY) == []

    def test_already_posted_excluded(self):
        big = trade(amount_min=1_000_001_00, amount_max=5_000_000_00)
        assert select_candidates([big], TODAY, already_posted={"t1"}) == []

    def test_rollup_for_big_filing(self):
        small = dict(amount_min=1_001_00, amount_max=15_000_00, notification_date=date(2026, 9, 5))
        trades = [trade(i, doc_id="docX", ticker=f"T{i}", **small) for i in range(6)]
        c = select_candidates(trades, TODAY)
        assert [x.kind for x in c] == ["rollup"]
        assert len(c[0].trades) == 6


class TestComposer:
    def test_trade_post_is_factual_and_fits(self):
        (c,) = select_candidates([trade(amount_min=250_001_00, amount_max=500_000_00)], TODAY)
        text, url = compose(c, BASE, TODAY)
        assert text.startswith("Sen. Tommy Tuberville (R-AL) disclosed a purchase of $INTC (Intel), $250,001 to $500,000.")
        assert "49 days, past the 45-day limit" in text
        assert url == f"{BASE}/t/t1?utm_source=x&utm_medium=social"
        assert x_length(text) <= X_LIMIT
        assert "—" not in text  # house style: no emdash

    def test_on_time_wording(self):
        (c,) = select_candidates([trade(amount_min=1_000_001_00, amount_max=5_000_000_00, notification_date=date(2026, 9, 11))], TODAY)
        text, _ = compose(c, BASE, TODAY)
        assert "(10 days)" in text and "limit" not in text

    def test_spouse_and_sale(self):
        (c,) = select_candidates(
            [trade(transaction_type="S", owner="SP", amount_min=500_001_00, amount_max=1_000_000_00, notification_date=date(2026, 9, 5))],
            TODAY,
        )
        text, _ = compose(c, BASE, TODAY)
        assert "a sale of $INTC (Intel) by a spouse" in text

    def test_rollup_fits(self):
        small = dict(amount_min=1_001_00, amount_max=15_000_00, notification_date=date(2026, 9, 5))
        trades = [trade(i, doc_id="docX", ticker=f"TICK{i}", member_name="Gilbert Ray Cisneros", party="D", state="CA", chamber="House", **small) for i in range(14)]
        (c,) = select_candidates(trades, TODAY)
        text, url = compose(c, BASE, TODAY)
        assert text.startswith("Rep. Gilbert Ray Cisneros (D-CA) disclosed 14 trades in one filing (14 buys)")
        assert "/members/m1" in url
        assert x_length(text) <= X_LIMIT

    def test_x_length_counts_urls_as_23(self):
        assert x_length("hi https://example.com/a/very/long/path/that/is/long") == 3 + 23

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Bank of Nova Scotia", "Bank of Nova Scotia"),
            ("Microsoft Corporation", "Microsoft"),
            ("Apple Inc.", "Apple"),
            (", .", ""),
            ("Greenbrier Affiliates : Description: H", ""),
            ("Marsh Common Stock", "Marsh"),
            ("XYZ Inc.", ""),
        ],
    )
    def test_clean_name(self, name, expected):
        assert clean_name(name, "XYZ") == expected

    def test_security_name_preferred_over_parsed_text(self):
        (c,) = select_candidates([trade(ticker="BNS", asset_name="Nova Scotia", security_name="Bank of Nova Scotia", amount_min=500_001_00, amount_max=1_000_000_00)], TODAY)
        text, _ = compose(c, BASE, TODAY)
        assert "$BNS (Bank of Nova Scotia)" in text

    def test_open_ended_range(self):
        assert amount_range(50_000_001_00, None) == "over $50,000,001"


class TestWindow:
    @pytest.mark.parametrize("hour,expected", [(11, False), (12, True), (23, True), (2, True), (3, False)])
    def test_wrapping_window(self, hour, expected):
        assert in_window(datetime(2026, 10, 23, hour, 30, tzinfo=timezone.utc), "12-3") is expected
