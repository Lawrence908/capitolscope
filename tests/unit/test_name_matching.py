"""
Tests for company-name -> ticker resolution (domains.securities.name_matching).
Precision-focused: exact normalized matches only, ambiguous names dropped.
"""

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.securities.name_matching import (
    normalize_company_name, build_name_index, resolve_ticker_by_name,
    looks_like_fixed_income, is_common_equity_target,
    build_containment_index, resolve_ticker_by_containment,
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


class TestNormalizeForeignSuffixes:
    def test_dotted_foreign_forms_stripped(self):
        assert normalize_company_name("Schlumberger N.V") == "schlumberger"
        assert normalize_company_name("Banco Santander, S.A.") == "banco santander"
        assert normalize_company_name("Cemex S.A.B. de C.V.") == "cemex"

    def test_unpaired_share_words_stripped(self):
        assert normalize_company_name("Accenture Ordinary") == "accenture"
        assert normalize_company_name("Linde Ordinary Share") == "linde"


class TestAmbiguityTiebreak:
    def test_prefers_active_plain_shortest(self):
        # Duke Energy: common DUK (active) beats the DUKB baby-bond listing.
        uni = {
            "DUK": {"name": "Duke Energy Corporation", "active": True},
            "DUKB": {"name": "Duke Energy Corporation", "active": True},
        }
        idx = build_name_index(uni)
        assert resolve_ticker_by_name("Duke Energy", idx) == "DUK"

    def test_active_beats_delisted(self):
        uni = {
            "NEW": {"name": "Example Corp", "active": True},
            "OLD": {"name": "Example Corp", "active": False},
        }
        idx = build_name_index(uni)
        assert resolve_ticker_by_name("Example", idx) == "NEW"

    def test_genuine_tie_still_dropped(self):
        # Equal on (active, plain, length) -> ambiguous -> dropped.
        uni = {"AAA": {"name": "Acme", "active": True}, "BBB": {"name": "Acme", "active": True}}
        assert resolve_ticker_by_name("Acme", build_name_index(uni)) is None


class TestFixedIncomeGuards:
    def test_detects_notes_and_coupons(self):
        assert looks_like_fixed_income("Aflac Inc Sr Nt 2.4% Due 03/16/20")
        assert looks_like_fixed_income("US Treasury Bill")
        assert looks_like_fixed_income("New York St Dorm Auth Rev")
        assert looks_like_fixed_income("Range Resources 5% Notes")

    def test_plain_equity_is_not_fixed_income(self):
        assert not looks_like_fixed_income("Apple Inc. Common Stock")
        assert not looks_like_fixed_income("NextEra Energy, Inc")

    def test_common_target_excludes_preferred_and_notes(self):
        assert is_common_equity_target({"name": "Apple Inc. Common Stock", "poly_type": "CS"})
        assert not is_common_equity_target({"name": "ViacomCBS Inc. 5.75% Series A Mandatory", "poly_type": "CS"})
        assert not is_common_equity_target({"name": "Some Co Pref", "poly_type": "PFD"})


class TestContainment:
    def _idx(self):
        uni = {
            "TSM": {"name": "Taiwan Semiconductor Manufacturing Company Ltd."},
            "CI": {"name": "The Cigna Group"},
            "CCI": {"name": "Crown Castle Inc."},
            "MRO": {"name": "Marathon Oil Corporation"},
            "MPC": {"name": "Marathon Petroleum Corporation"},
            "ATCO": {"name": "Atlas Corp."},
        }
        ni = build_name_index(uni)
        return ni, build_containment_index(ni)

    def test_subset_query_matches_verbose_listing(self):
        ni, cidx = self._idx()
        # query ⊆ listing name
        assert resolve_ticker_by_containment("Taiwan Semiconductor", ni, cidx) == "TSM"
        assert resolve_ticker_by_containment("Cigna", ni, cidx) == "CI"

    def test_superset_query_matches_shorter_listing(self):
        ni, cidx = self._idx()
        # query has an extra descriptor; listing name (>=2 tokens) is a subset
        assert resolve_ticker_by_containment("Crown Castle International", ni, cidx) == "CCI"

    def test_sibling_names_do_not_cross_match(self):
        ni, cidx = self._idx()
        # "Marathon" alone would hit both MRO and MPC -> ambiguous -> None
        assert resolve_ticker_by_containment("Marathon", ni, cidx) is None

    def test_one_word_listing_cannot_swallow_longer_name(self):
        ni, cidx = self._idx()
        # "Atlas Corp" (one content token "atlas") must not match "Atlas Copco"
        assert resolve_ticker_by_containment("Atlas Copco AB", ni, cidx) is None

    def test_fixed_income_never_matches(self):
        ni, cidx = self._idx()
        assert resolve_ticker_by_containment("Cigna 3.2% Notes Due 2027", ni, cidx) is None


class TestSecurityMatcher:
    """The shared resolver used by both the backfill and live ingestion."""

    def _matcher(self):
        from domains.securities.matching import SecurityMatcher
        # Small in-memory universe avoids any network/Polygon load.
        universe_meta = {
            "AAPL": {"name": "Apple Inc.", "active": True, "asset_type": "STOCK"},
            "TSM": {"name": "Taiwan Semiconductor Manufacturing Company", "active": True, "asset_type": "STOCK"},
            "MON": {"name": "Monument Circle Acquisition Corp.", "active": True, "asset_type": "STOCK"},
        }
        return SecurityMatcher(universe_meta=universe_meta)

    def test_name_and_containment(self):
        m = self._matcher()
        assert m.resolve(None, "Apple Inc. Common Stock") == ("AAPL", "name")
        assert m.resolve(None, "Taiwan Semiconductor") == ("TSM", "containment")

    def test_fixed_income_never_matches(self):
        m = self._matcher()
        assert m.resolve(None, "Apple Inc 3.25% Notes Due 2029") == (None, "fixed_income")
        # Not even via a stored ticker.
        assert m.resolve("AAPL", "Apple Inc 3.25% Notes Due 2029") == (None, "fixed_income")

    def test_reused_ticker_name_is_not_matched(self):
        m = self._matcher()
        # "Monsanto" -> MON, but MON is now an unrelated active SPAC: must not match.
        assert m.resolve("MON", "Monsanto Company") == (None, "unresolved")

    def test_embedded_fund_symbol(self):
        m = self._matcher()
        assert m.resolve(None, "BLF FedFund TDDXX") == ("TDDXX", "fund")

    def test_security_seed_flags_fund_and_delisted(self):
        m = self._matcher()
        assert m.security_seed("TDDXX", "fund", "BLF FedFund")["asset_type_code"] == "MF"
        assert m.security_seed("AAPL", "name")["is_active"] is True


class TestFundTicker:
    def test_extracts_embedded_fund_symbol(self):
        from domains.securities.ticker_cleaning import extract_fund_ticker
        assert extract_fund_ticker("BLF FedFund TDDXX") == "TDDXX"
        assert extract_fund_ticker("Vanguard 500 Index Fund VFIAX") == "VFIAX"

    def test_ignores_non_fund_text(self):
        from domains.securities.ticker_cleaning import extract_fund_ticker
        assert extract_fund_ticker("Apple Inc. Common Stock") is None
        assert extract_fund_ticker("Microsoft Corporation") is None
        assert extract_fund_ticker(None) is None
