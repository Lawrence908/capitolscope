"""
Tests for the standalone TickerExtractor (domains.congressional.ticker_extraction).

This is a second, simpler ticker extractor that coexists with the one inside
DataQualityEnhancer. Pinning its behavior here documents the overlap (useful
context for the eventual consolidation) and locks in the pieces other code
depends on, notably normalize_ticker's Yahoo-Finance dot->dash convention.
"""

from decimal import Decimal

import pytest

from domains.congressional.ticker_extraction import TickerExtractionResult, TickerExtractor

pytestmark = pytest.mark.unit


class TestExtractFromDescription:
    def test_empty_description(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description("")
        assert result.ticker is None
        assert result.method == "empty_description"

    def test_ticker_in_parentheses(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description("Some Company (MSFT)")
        assert result.ticker == "MSFT"
        assert result.method.startswith("regex_pattern")
        assert result.confidence == 0.9

    def test_ticker_after_dash_at_end(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description("Widget Corp - AAPL")
        assert result.ticker == "AAPL"

    def test_symbol_prefix(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description("Symbol: TSLA")
        assert result.ticker == "TSLA"

    def test_company_name_exact_fuzzy_match(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description(
            "Apple Inc common stock"
        )
        assert result.ticker == "AAPL"
        assert result.method == "fuzzy_exact_match"


class TestIsValidTicker:
    @pytest.mark.parametrize("value", ["AAPL", "MSFT", "V", "BRK"])
    def test_accepts_valid_tickers(self, ticker_extractor, value):
        assert ticker_extractor._is_valid_ticker(value) is True

    @pytest.mark.parametrize(
        "value",
        ["THE", "INC", "ETF", "TRUST", "aapl", "TOOLONG", "", "A1"],
    )
    def test_rejects_invalid_tickers(self, ticker_extractor, value):
        assert ticker_extractor._is_valid_ticker(value) is False


class TestNormalizeTicker:
    def test_uppercases_and_trims(self, ticker_extractor):
        assert ticker_extractor.normalize_ticker(" aapl ") == "AAPL"

    def test_dot_becomes_dash_for_yahoo(self, ticker_extractor):
        # BRK.B is quoted as BRK-B by Yahoo Finance; price fetching relies on it.
        assert ticker_extractor.normalize_ticker("BRK.B") == "BRK-B"

    def test_empty_returns_empty_string(self, ticker_extractor):
        assert ticker_extractor.normalize_ticker("") == ""

    def test_strips_trailing_parenthetical(self, ticker_extractor):
        assert ticker_extractor.normalize_ticker("AAPL (Apple)") == "AAPL"


class TestResultDefaults:
    def test_result_has_sane_defaults(self):
        r = TickerExtractionResult()
        assert r.ticker is None
        assert isinstance(r.notes, list)


class TestKnownIssues:
    @pytest.mark.xfail(
        reason="Heuristic word-match accepts any non-excluded 4-letter uppercase "
        "word ('HERE') as a ticker.",
        strict=False,
    )
    def test_plain_text_should_not_yield_false_ticker(self, ticker_extractor):
        result = ticker_extractor.extract_ticker_from_description("nothing here")
        assert result.ticker is None
