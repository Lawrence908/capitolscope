"""
Tests for the public trade page helpers (permalink, ticker page, feeds).
"""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from domains.congressional.trade_links import (
    DISCLOSURE_LIMIT_DAYS,
    days_to_disclose,
    downsample,
    filing_document_url,
    infer_chamber,
    is_amended,
    is_late,
    price_on_or_before,
    summarize_ticker_trades,
)

pytestmark = pytest.mark.unit

SENATE_DOC = "fda235b3-bad7-4637-8fa1-053f354d929c"


class TestInferChamber:
    def test_known_chamber_wins(self):
        assert infer_chamber("Senate", "20027931") == "Senate"
        assert infer_chamber("house", SENATE_DOC) == "House"

    def test_enum_like_value(self):
        assert infer_chamber(SimpleNamespace(value="Senate"), None) == "Senate"

    def test_falls_back_to_doc_id_format(self):
        assert infer_chamber(None, "20027931") == "House"
        assert infer_chamber("", SENATE_DOC) == "Senate"

    def test_unknown(self):
        assert infer_chamber(None, None) is None
        assert infer_chamber(None, "abc") is None


class TestFilingDocumentUrl:
    def test_stored_url_is_used(self):
        assert filing_document_url("20027931", " https://x/y.pdf ", date(2025, 3, 7)) == "https://x/y.pdf"

    def test_house_pdf_from_filing_year(self):
        assert (
            filing_document_url("20027931", None, date(2025, 3, 7), "House")
            == "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20027931.pdf"
        )

    def test_house_inferred_without_chamber(self):
        assert filing_document_url("20001516", "", date(2014, 8, 4)).endswith("/ptr-pdfs/2014/20001516.pdf")

    def test_house_needs_filing_date(self):
        assert filing_document_url("20027931", None, None, "House") is None

    def test_senate_ptr(self):
        assert (
            filing_document_url(SENATE_DOC.upper(), None, date(2026, 7, 21))
            == f"https://efdsearch.senate.gov/search/view/ptr/{SENATE_DOC}/"
        )

    def test_numeric_doc_for_senator_is_not_guessed(self):
        assert filing_document_url("20027931", None, date(2025, 1, 1), "Senate") is None

    def test_missing(self):
        assert filing_document_url(None) is None
        assert filing_document_url("not-a-doc", None, date(2025, 1, 1)) is None


class TestTiming:
    def test_days(self):
        assert days_to_disclose(date(2024, 5, 7), date(2026, 8, 5)) == 820
        assert days_to_disclose(date(2024, 5, 7), date(2024, 5, 7)) == 0

    def test_days_never_negative_or_unknown(self):
        assert days_to_disclose(date(2024, 5, 7), date(2024, 5, 1)) == 0
        assert days_to_disclose(None, date(2024, 5, 1)) is None

    def test_amended(self):
        assert is_amended("A")
        assert is_amended(SimpleNamespace(value="A"))
        assert not is_amended("N")
        assert not is_amended(None)

    def test_late(self):
        assert is_late(DISCLOSURE_LIMIT_DAYS + 1)
        assert not is_late(DISCLOSURE_LIMIT_DAYS)
        assert not is_late(None)

    def test_amended_is_never_late(self):
        assert not is_late(400, amended=True)


class TestDownsample:
    def test_short_series_untouched(self):
        assert downsample([1, 2, 3], 5) == [1, 2, 3]

    def test_keeps_endpoints_and_cap(self):
        pts = list(range(1000))
        out = downsample(pts, 100)
        assert out[0] == 0 and out[-1] == 999
        assert len(out) <= 100
        assert out == sorted(out)

    def test_edge_caps(self):
        assert downsample([1, 2, 3], 0) == []
        assert downsample([1, 2, 3], 1) == [3]


class TestPriceOnOrBefore:
    series = [(date(2024, 5, 6), 30), (date(2024, 5, 7), 31), (date(2024, 5, 10), 33)]

    def test_exact(self):
        assert price_on_or_before(self.series, date(2024, 5, 7)) == 31

    def test_weekend_uses_prior_close(self):
        assert price_on_or_before(self.series, date(2024, 5, 9)) == 31

    def test_before_history(self):
        assert price_on_or_before(self.series, date(2024, 1, 1)) is None

    def test_missing_inputs(self):
        assert price_on_or_before([], date(2024, 5, 7)) is None
        assert price_on_or_before(self.series, None) is None


class TestSummarize:
    def test_stats(self):
        a, b = str(uuid.uuid4()), str(uuid.uuid4())
        rows = [
            {"member_id": a, "transaction_type": "P", "transaction_date": "2024-01-02",
             "notification_date": "2024-01-20", "days_to_disclose": 18, "filing_status": "N"},
            {"member_id": a, "transaction_type": "S", "transaction_date": "2024-03-02",
             "notification_date": "2024-06-20", "days_to_disclose": 110, "filing_status": "N"},
            {"member_id": b, "transaction_type": "S", "transaction_date": "2023-03-02",
             "notification_date": "2024-06-21", "days_to_disclose": 477, "filing_status": "A"},
            {"member_id": b, "transaction_type": "E", "transaction_date": None,
             "notification_date": None, "days_to_disclose": None, "filing_status": None},
        ]
        s = summarize_ticker_trades(rows)
        assert s["trades"] == 4
        assert s["members"] == 2
        assert (s["buys"], s["sells"], s["other"]) == (1, 2, 1)
        assert s["late"] == 1  # the amended one is not counted
        assert s["first_trade_date"] == "2023-03-02"
        assert s["latest_trade_date"] == "2024-03-02"
        assert s["latest_filing_date"] == "2024-06-21"

    def test_empty(self):
        s = summarize_ticker_trades([])
        assert s["trades"] == 0 and s["latest_trade_date"] is None


class TestApiHelpers:
    """Pure helpers in api.trades (feed row shaping, date clamp)."""

    def test_clamp(self):
        from api.trades import clamp_transaction_date_to

        today = date(2026, 10, 23)
        assert clamp_transaction_date_to(None, today) == today
        assert clamp_transaction_date_to(date(2027, 1, 1), today) == today
        assert clamp_transaction_date_to(date(2025, 1, 1), today) == date(2025, 1, 1)

    def test_feed_item_shape(self):
        from api.trades import trade_feed_item

        tid, mid = uuid.uuid4(), uuid.uuid4()
        trade = SimpleNamespace(
            id=tid, member_id=mid, doc_id="20027931", ticker="INTC", asset_name=None,
            raw_asset_description="Intel Corp (INTC)", asset_type="Stock", transaction_type="P",
            transaction_date=date(2025, 2, 26), notification_date=date(2025, 3, 7),
            amount_min=100_100, amount_max=1_500_000, amount_exact=None, owner="SP",
            filing_status="N", security_id=None,
        )
        member = SimpleNamespace(full_name="Jane Doe", party="D", state="CA", district="12", chamber=None)
        item = trade_feed_item(trade, member)
        assert item["id"] == str(tid) and item["member_id"] == str(mid)
        assert item["member_chamber"] == "House"  # inferred from the Clerk doc id
        assert item["asset_name"] == "Intel Corp (INTC)"  # falls back to the raw description
        assert item["transaction_date"] == "2025-02-26"
        assert item["days_to_disclose"] == 9
        assert item["amount_min"] == 100_100 and item["security_id"] is None
