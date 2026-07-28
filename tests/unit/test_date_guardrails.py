"""
Guardrails for date parsing in the congressional ingestion pipeline.

Scanned House PTR PDFs and Senate eFD transcription produce garbage years
(OCR of 2031 -> 3031, digit doubling -> 2220 / 2202) and occasional
future-dated filings. These must never reach the DB: _parse_date /
_bounded_date drop them so the row falls back to inference or is recorded as
an invalid_date error. See the "Recent Trades" bug where 4/29/3031, 4/6/2220,
9/18/2202 and 12/25/2026 were displayed.
"""

from datetime import date, timedelta

import pytest

from domains.congressional.ingestion import CongressionalDataIngestion, ProcessedTrade
from domains.congressional.pdf_parser import PDFParsingValidator

pytestmark = pytest.mark.unit


@pytest.fixture
def ingester():
    # _parse_date / _bounded_date are pure and only read the class-level
    # MIN_TRADE_DATE; skip __init__ so no live DB (ticker load) is needed.
    return CongressionalDataIngestion.__new__(CongressionalDataIngestion)


def _make_trade(transaction_date, notification_date):
    """Build a minimal otherwise-valid ProcessedTrade for _validate_trade."""
    trade = ProcessedTrade.__new__(ProcessedTrade)
    trade.doc_id = "20000001"
    trade.member_id = "00000000-0000-0000-0000-000000000001"
    trade.transaction_type = "P"
    trade.transaction_date = transaction_date
    trade.notification_date = notification_date
    trade.owner = "SP"
    trade.amount_min = 1001
    trade.amount_max = 15000
    trade.amount_exact = None
    trade.parsing_notes = []
    trade.validation_errors = []
    trade.is_valid = True
    return trade


class TestParseDateGuardrails:
    @pytest.mark.parametrize(
        "raw",
        ["4/29/3031", "4/6/2220", "9/18/2202", "3031", "01/01/2200"],
    )
    def test_garbage_future_years_rejected(self, ingester, raw):
        assert ingester._parse_date(raw) is None

    def test_future_date_within_current_year_rejected(self, ingester):
        # 12/25/2026 style: valid syntax, plausible year, but not yet happened.
        future = date.today() + timedelta(days=30)
        assert ingester._parse_date(future.strftime("%m/%d/%Y")) is None

    def test_pre_floor_date_rejected(self, ingester):
        assert ingester._parse_date("1/1/1999") is None

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2021-03-15", date(2021, 3, 15)),
            ("01/15/2024", date(2024, 1, 15)),
            ("2/18/22", date(2022, 2, 18)),
        ],
    )
    def test_valid_past_dates_pass(self, ingester, raw, expected):
        assert ingester._parse_date(raw) == expected

    def test_today_is_allowed(self, ingester):
        today = date.today()
        assert ingester._parse_date(today.strftime("%m/%d/%Y")) == today


class TestNotificationOrderingNormalization:
    """notification_date must never precede transaction_date once persisted.

    Transcription typos (wrong year/month, Jan-1 placeholders, swapped fields)
    produce that impossible ordering; _validate_trade collapses it up to the
    transaction_date instead of dropping the trade or persisting a bogus date.
    """

    def test_notif_before_txn_is_collapsed_to_txn(self, ingester):
        trade = _make_trade(date(2022, 9, 29), date(2020, 9, 29))
        ingester._validate_trade(trade)
        assert trade.notification_date == date(2022, 9, 29)
        assert "notification_date_before_transaction_date" in trade.parsing_notes
        assert trade.is_valid is True

    def test_notif_equal_to_txn_is_untouched(self, ingester):
        trade = _make_trade(date(2022, 9, 29), date(2022, 9, 29))
        ingester._validate_trade(trade)
        assert trade.notification_date == date(2022, 9, 29)
        assert "notification_date_before_transaction_date" not in trade.parsing_notes

    def test_notif_after_txn_is_untouched(self, ingester):
        trade = _make_trade(date(2022, 9, 29), date(2022, 10, 5))
        ingester._validate_trade(trade)
        assert trade.notification_date == date(2022, 10, 5)
        assert "notification_date_before_transaction_date" not in trade.parsing_notes


class TestPdfValidatorGuardrails:
    def setup_method(self):
        self.validator = PDFParsingValidator()

    @pytest.mark.parametrize(
        "raw",
        ["04/29/3031", "04/06/2220", "09/18/2202"],
    )
    def test_garbage_years_invalid(self, raw):
        assert self.validator._is_valid_date(raw) is False

    def test_future_date_invalid(self):
        future = date.today() + timedelta(days=30)
        assert self.validator._is_valid_date(future.strftime("%m/%d/%Y")) is False

    def test_valid_past_date(self):
        assert self.validator._is_valid_date("01/15/2024") is True
