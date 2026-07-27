"""
Tests for company-name -> ticker resolution (domains.securities.name_matching).
Precision-focused: exact normalized matches only, ambiguous names dropped.
"""

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.securities.name_matching import (
    normalize_company_name, build_name_index, resolve_ticker_by_name,
)

pytestmark = pytest.mark.unit


class TestNormalize:
    def test_strips_legal_suffixes_and_punctuation(self):
        assert normalize_company_name("NextEra Energy, Inc.") == "nextera energy"
        assert normalize_company_name("3M Company") == "3m"
        assert normalize_company_name("Honeywell International Inc") == "honeywell international"
        assert normalize_company_name("Markel Group Inc. Common Stock") == "markel group"

    def test_class_shares_and_ampersand(self):
        assert normalize_company_name("Affirm Holdings, Inc. - Class A") == "affirm holdings"
        assert normalize_company_name("Xenia Hotels & Resorts, Inc") == "xenia hotels and resorts"

    def test_empty(self):
        assert normalize_company_name(None) == ""
        assert normalize_company_name("   ") == ""

    def test_fund_boilerplate_stripped(self):
        # ETF/fund tokens are stripped so "Trust" and "Shares" variants align.
        assert normalize_company_name("SPDR Gold Trust") == "spdr gold"
        assert normalize_company_name("SPDR Gold Shares") == "spdr gold"
        assert normalize_company_name("Vanguard FTSE Emerging Markets ETF") == "vanguard ftse emerging markets"


class TestIndexAndResolve:
    def _uni(self):
        return {
            "NEE": {"name": "NextEra Energy, Inc."},
            "MMM": {"name": "3M Company"},
            "AFRM": {"name": "Affirm Holdings, Inc."},
        }

    def test_build_index_and_exact_resolve(self):
        idx = build_name_index(self._uni())
        assert resolve_ticker_by_name("NextEra Energy, Inc", idx) == "NEE"
        assert resolve_ticker_by_name("3M COMPANY", idx) == "MMM"
        assert resolve_ticker_by_name("Affirm Holdings Inc - Class A", idx) == "AFRM"

    def test_unknown_returns_none(self):
        idx = build_name_index(self._uni())
        assert resolve_ticker_by_name("Some Private LLC", idx) is None
        assert resolve_ticker_by_name("", idx) is None

    def test_ambiguous_names_are_dropped(self):
        # Two different tickers normalizing to the same name -> not indexed.
        uni = {"AAA": {"name": "Acme Corporation"}, "BBB": {"name": "Acme Corp"}}
        idx = build_name_index(uni)
        assert resolve_ticker_by_name("Acme", idx) is None
