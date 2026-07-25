"""
Tests for DataQualityEnhancer — the congressional-trade data cleaning engine.

This is the most bug-prone "layered" subsystem (ticker extraction, amount
normalization, owner normalization), so behavior is pinned in detail. The
TestKnownIssues class uses xfail to document behavior that is currently wrong
and *should* change — those tests will start xpassing once the ship is righted,
which is the signal to tighten them into hard assertions.
"""

from decimal import Decimal

import pytest

from domains.congressional.data_quality import (
    AmountNormalizationResult,
    DataQualityEnhancer,
    OwnerNormalizationResult,
    TickerExtractionResult,
)
from domains.congressional.schemas import TradeOwner

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Ticker extraction
# ---------------------------------------------------------------------------
class TestTickerExtraction:
    def test_empty_description_returns_no_input(self, enhancer):
        result = enhancer.extract_ticker("")
        assert isinstance(result, TickerExtractionResult)
        assert result.ticker is None
        assert result.extraction_method == "no_input"
        assert result.confidence == Decimal("0.0")

    def test_known_company_maps_to_ticker(self, enhancer):
        result = enhancer.extract_ticker("MICROSOFT CORPORATION")
        assert result.ticker == "MSFT"
        assert result.extraction_method == "company_mapping"
        assert result.confidence >= Decimal("0.9")

    def test_company_mapping_takes_priority_over_regex(self, enhancer):
        # "Apple Inc" contains both a mappable company name and stray uppercase
        # tokens; the company mapping must win.
        result = enhancer.extract_ticker("Apple Inc")
        assert result.ticker == "AAPL"
        assert result.extraction_method == "company_mapping"

    def test_etf_trust_name_maps_to_etf_ticker(self, enhancer):
        result = enhancer.extract_ticker("SPDR S&P 500 ETF TRUST")
        assert result.ticker == "SPY"

    def test_short_ticker_confidence_is_penalised(self, enhancer):
        # 4-letter AAPL gets a 0.9 length multiplier on the 0.95 base.
        result = enhancer.extract_ticker("Apple Inc")
        assert result.confidence == Decimal("0.95") * Decimal("0.9")

    def test_confidence_never_exceeds_one(self, enhancer):
        result = enhancer.extract_ticker("MICROSOFT CORPORATION MICROSOFT")
        assert result.confidence <= Decimal("1.0")

    def test_asset_type_detection_defaults_to_stock(self, enhancer):
        result = enhancer.extract_ticker("MICROSOFT CORPORATION")
        assert result.asset_type == "STOCK"

    def test_bond_description_detected_as_bond(self, enhancer):
        result = enhancer.extract_ticker("US Treasury Bond 2.5%")
        assert result.asset_type == "BOND"


# ---------------------------------------------------------------------------
# Amount normalization
# ---------------------------------------------------------------------------
class TestAmountNormalization:
    def test_empty_amount(self, enhancer):
        result = enhancer.normalize_amount("")
        assert isinstance(result, AmountNormalizationResult)
        assert result.amount_min is None and result.amount_max is None
        assert result.confidence == Decimal("0.0")

    def test_standard_range_exact_match(self, enhancer):
        # Values are stored in cents: $1,001 -> 100100, $15,000 -> 1500000.
        result = enhancer.normalize_amount("$1,001 - $15,000")
        assert result.amount_min == 100100
        assert result.amount_max == 1500000
        assert result.confidence == Decimal("0.95")

    def test_range_without_spaces_is_normalised(self, enhancer):
        result = enhancer.normalize_amount("$15,001-$50,000")
        assert result.amount_min == 1500100
        assert result.amount_max == 5000000

    def test_dollarless_variation_is_mapped(self, enhancer):
        result = enhancer.normalize_amount("1,001 - 15,000")
        assert result.amount_min == 100100
        assert result.amount_max == 1500000

    def test_open_ended_top_range(self, enhancer):
        result = enhancer.normalize_amount("$50,000,000+")
        assert result.amount_min == 5000000000
        assert result.amount_max is None

    def test_garbage_trailing_characters_are_stripped(self, enhancer):
        result = enhancer.normalize_amount("$5,000abc")
        assert result.amount_exact == 500000  # $5,000 in cents
        assert any("garbage" in note.lower() for note in result.notes)

    def test_unparseable_amount_yields_zero_confidence(self, enhancer):
        result = enhancer.normalize_amount("not a number")
        assert result.amount_min is None
        assert result.amount_max is None
        assert result.amount_exact is None
        assert result.confidence == Decimal("0.0")

    def test_original_amount_is_preserved(self, enhancer):
        result = enhancer.normalize_amount("$5,000abc")
        assert result.original_amount == "$5,000abc"


# ---------------------------------------------------------------------------
# Owner normalization
# ---------------------------------------------------------------------------
class TestOwnerNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("C", TradeOwner.SELF),
            ("SP", TradeOwner.SPOUSE),
            ("JT", TradeOwner.JOINT),
            ("DC", TradeOwner.DEPENDENT_CHILD),
        ],
    )
    def test_standard_code_mapping(self, enhancer, raw, expected):
        result = enhancer.normalize_owner(raw)
        assert result.normalized_owner == expected
        assert result.confidence == Decimal("0.95")

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("spouse", TradeOwner.SPOUSE),
            ("JOINT", TradeOwner.JOINT),
            ("dependent child", TradeOwner.DEPENDENT_CHILD),
            ("self", TradeOwner.SELF),
        ],
    )
    def test_full_text_mapping_case_insensitive(self, enhancer, raw, expected):
        assert enhancer.normalize_owner(raw).normalized_owner == expected

    def test_empty_owner(self, enhancer):
        result = enhancer.normalize_owner("")
        assert isinstance(result, OwnerNormalizationResult)
        assert result.normalized_owner is None
        assert result.confidence == Decimal("0.0")

    def test_person_name_assumed_self_as_misalignment(self, enhancer):
        # A member name in the owner column is treated as data misalignment and
        # assumed to be SELF at low confidence.
        result = enhancer.normalize_owner("Nancy Pelosi")
        assert result.normalized_owner == TradeOwner.SELF
        assert result.confidence == Decimal("0.50")
        assert any("misalignment" in note.lower() for note in result.notes)

    def test_family_trust_assumed_joint(self, enhancer):
        result = enhancer.normalize_owner("Acme Family Trust LLC")
        assert result.normalized_owner == TradeOwner.JOINT
        assert result.confidence == Decimal("0.60")

    def test_unmappable_token_returns_none(self, enhancer):
        result = enhancer.normalize_owner("xyz")
        assert result.normalized_owner is None
        assert result.confidence == Decimal("0.0")


# ---------------------------------------------------------------------------
# Aggregate quality analysis
# ---------------------------------------------------------------------------
class TestAnalyzeDataQuality:
    def test_empty_sample_returns_error(self, enhancer):
        assert "error" in enhancer.analyze_data_quality([])

    def test_analysis_reports_rates(self, enhancer):
        records = [
            {
                "raw_asset_description": "MICROSOFT CORPORATION",
                "amount": "$1,001 - $15,000",
                "owner": "C",
            },
            {
                "raw_asset_description": "Apple Inc",
                "amount": "$15,001 - $50,000",
                "owner": "SP",
            },
        ]
        analysis = enhancer.analyze_data_quality(records)
        assert analysis["total_records"] == 2
        assert analysis["ticker_analysis"]["success_rate"] == 100.0
        assert analysis["amount_analysis"]["success_rate"] == 100.0
        assert analysis["owner_analysis"]["success_rate"] == 100.0


# ---------------------------------------------------------------------------
# Known issues — documented, expected-to-change behavior.
# These xfail today; when the extractor is fixed they will xpass, prompting us
# to convert them into hard assertions. Not counted as suite failures.
# ---------------------------------------------------------------------------
class TestKnownIssues:
    @pytest.mark.xfail(
        reason="Regex ticker pass extracts a false-positive ticker ('SOME') "
        "from plain-English descriptions with no real ticker.",
        strict=False,
    )
    def test_plain_english_should_not_yield_false_ticker(self, enhancer):
        result = enhancer.extract_ticker("Some random farmland in Iowa")
        assert result.ticker is None

    @pytest.mark.xfail(
        reason="A bare uppercase word is accepted as a ticker with 0.8 "
        "confidence even when it is an ordinary English word.",
        strict=False,
    )
    def test_ordinary_word_should_not_be_high_confidence_ticker(self, enhancer):
        result = enhancer.extract_ticker("BUY low SELL high")
        assert result.confidence < Decimal("0.5")


def test_enhancer_is_constructible_without_network():
    """The LocalTickerResolver must default to disabled (no Ollama call)."""
    e = DataQualityEnhancer()
    assert e.local_ticker_resolver.enabled is False
