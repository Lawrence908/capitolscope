"""
Tests for congress-member identity enrichment
(domains.congressional.member_enrichment). Precision-first: ambiguous or
surname-only hits must never come back as ``matched``.
"""

from datetime import date

import pytest

from domains.congressional.member_enrichment import (
    STATUS_AMBIGUOUS,
    STATUS_DUPLICATE,
    STATUS_MATCHED,
    STATUS_REVIEW,
    STATUS_UNMATCHED,
    MemberRecord,
    build_index,
    first_name_strength,
    map_party,
    match_member,
    match_members,
    normalize_token,
    surname_keys,
)

pytestmark = pytest.mark.unit


def _term(kind, start, end, state, party, district=None, **extra):
    t = {"type": kind, "start": start, "end": end, "state": state, "party": party}
    if district is not None:
        t["district"] = district
    t.update(extra)
    return t


def _leg(bioguide, first, last, terms, middle=None, nickname=None, suffix=None, official=None):
    name = {"first": first, "last": last}
    for k, v in (("middle", middle), ("nickname", nickname), ("suffix", suffix), ("official_full", official)):
        if v:
            name[k] = v
    return {"id": {"bioguide": bioguide}, "name": name, "terms": terms}


HISTORICAL = [
    _leg("M001193", "Thomas", "MacArthur", [
        _term("rep", "2015-01-06", "2017-01-03", "NJ", "Republican", 3),
        _term("rep", "2017-01-03", "2019-01-03", "NJ", "Republican", 3),
    ], official="Thomas MacArthur"),
    _leg("C001062", "K.", "Conaway", [
        _term("rep", "2005-01-04", "2021-01-03", "TX", "Republican", 11),
    ], middle="Michael", official="K. Michael Conaway"),
    _leg("M001180", "David", "McKinley", [
        _term("rep", "2011-01-05", "2023-01-03", "WV", "Republican", 1),
    ], middle="B."),
    _leg("R000583", "Thomas", "Rooney", [
        _term("rep", "2009-01-06", "2019-01-03", "FL", "Republican", 17),
    ], middle="J."),
    _leg("P000096", "Bill", "Pascrell", [
        _term("rep", "1997-01-07", "2024-08-21", "NJ", "Democrat", 9),
    ], suffix="Jr."),
    _leg("O000170", "Beto", "O’Rourke", [
        _term("rep", "2013-01-03", "2019-01-03", "TX", "Democrat", 16),
    ]),
    _leg("A000367", "Justin", "Amash", [
        _term("rep", "2017-01-03", "2019-01-03", "MI", "Republican", 3),
        _term("rep", "2019-01-03", "2021-01-03", "MI", "Libertarian", 3, party_affiliations=[
            {"start": "2019-01-03", "end": "2019-07-03", "party": "Republican"},
            {"start": "2019-07-04", "end": "2020-04-30", "party": "Independent"},
            {"start": "2020-05-01", "end": "2021-01-03", "party": "Libertarian"},
        ]),
    ]),
    # Two Smiths serving at the same time with compatible first names.
    _leg("S900001", "John", "Smith", [_term("rep", "2015-01-03", "2021-01-03", "OH", "Republican", 2)]),
    _leg("S900002", "Jack", "Smith", [_term("rep", "2017-01-03", "2023-01-03", "PA", "Democrat", 5)]),
    # A 19th-century namesake who must be filtered out by the trade window.
    _leg("G000001", "Greg", "Gianforte", [_term("rep", "1801-01-01", "1803-03-03", "MT", "Federalist")]),
    _leg("C001104", "Madison", "Cawthorn", [_term("rep", "2021-01-03", "2023-01-03", "NC", "Republican", 11)]),
    _leg("B000490", "Sanford", "Bishop", [_term("rep", "1993-01-05", "2027-01-03", "GA", "Democrat", 2)],
         middle="D.", suffix="Jr."),
]

CURRENT = [
    _leg("G000584", "Greg", "Gianforte", [
        _term("rep", "2017-06-21", "2021-01-03", "MT", "Republican", 0),
    ]),
    _leg("M001159", "Cathy", "McMorris Rodgers", [
        _term("rep", "2005-01-04", "2025-01-03", "WA", "Republican", 5),
    ]),
    _leg("V000139", "Matt", "Van Epps", [_term("rep", "2025-12-04", "2027-01-03", "TN", "Republican", 7)]),
    _leg("A000383", "Alan", "Armstrong", [_term("sen", "2026-03-24", "2027-01-03", "OK", "Republican")]),
    _leg("H001072", "J.", "Hill", [_term("rep", "2015-01-06", "2027-01-03", "AR", "Republican", 2)],
         middle="French", official="J. French Hill"),
    _leg("B001311", "Dan", "Bishop", [_term("rep", "2019-09-17", "2025-01-03", "NC", "Republican", 8)]),
]


@pytest.fixture(scope="module")
def index_and_terms():
    return build_index(CURRENT, HISTORICAL)


def _member(full, first, last, lo, hi, n=10, prefix="Hon."):
    return MemberRecord(
        id=f"id-{full}", first_name=first, last_name=last, full_name=full, prefix=prefix,
        first_trade=date.fromisoformat(lo) if lo else None,
        last_trade=date.fromisoformat(hi) if hi else None, trade_count=n,
    )


def _match(index_and_terms, member):
    index, raw = index_and_terms
    return match_member(member, index, raw_terms=raw)


class TestNormalization:
    def test_tokens(self):
        assert normalize_token("Rubén") == "ruben"
        assert normalize_token("O’Rourke") == normalize_token("O'Rourke") == "orourke"
        assert normalize_token("Mckinley") == normalize_token("McKinley")
        assert normalize_token(None) == ""

    def test_surname_keys_drop_suffix_and_index_compound(self):
        assert surname_keys("Pascrell, Jr.") == ["pascrell"]
        assert surname_keys("McMorris Rodgers") == ["mcmorris rodgers", "mcmorrisrodgers", "rodgers"]
        assert surname_keys("Jr.") == []

    def test_first_name_strength(self):
        assert first_name_strength(["tom"], ["thomas"]) == 2
        assert first_name_strength(["kenneth"], ["ken"]) == 2
        assert first_name_strength(["k"], ["k", "michael"]) == 1        # initial
        assert first_name_strength(["matthew"], ["matt"]) == 2
        assert first_name_strength(["aston"], ["a", "donald"]) == 1      # initial
        assert first_name_strength(["edward"], ["theodore"]) == 0        # both "ted", not each other
        assert first_name_strength(["david"], ["madison"]) == 0

    def test_map_party(self):
        assert map_party("Democrat") == "D"
        assert map_party("Republican") == "R"
        assert map_party("Independent") == "I"
        assert map_party("Libertarian") is None
        assert map_party(None) is None


class TestMatching:
    def test_case_and_window_filter_historic_namesake(self, index_and_terms):
        r = _match(index_and_terms, _member("Greg Gianforte", "Greg", "Gianforte", "2017-06-30", "2020-12-21"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "G000584"
        f = r.proposed_fields()
        assert f["chamber"] == "House" and f["state"] == "MT" and f["party"] == "R"
        assert "district" not in f            # at-large stays NULL like existing rows
        assert "term_end" not in f            # current member keeps term_end NULL

    def test_mixed_case_surname_and_last_overlapping_term(self, index_and_terms):
        r = _match(index_and_terms, _member("Thomas Macarthur", "Thomas", "MacArthur", "2015-01-02", "2019-12-21"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "M001193"
        assert r.term.start == date(2017, 1, 3)
        f = r.proposed_fields()
        assert f == {
            "bioguide_id": "M001193", "party": "R", "chamber": "House", "state": "NJ",
            "district": "3", "term_start": date(2015, 1, 6), "term_end": date(2019, 1, 3),
        }

    def test_nickname_tom_thomas(self, index_and_terms):
        r = _match(index_and_terms, _member("Tom Rooney", "Tom", "Rooney", "2014-01-23", "2019-01-02"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "R000583"

    def test_initial_first_name(self, index_and_terms):
        r = _match(index_and_terms, _member("K. Conaway", "K.", "Conaway", "2013-07-01", "2020-12-21"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "C001062"
        assert r.term.state == "TX" and r.term.district == "11"

    def test_mckinley_and_suffix_and_apostrophe(self, index_and_terms):
        assert _match(index_and_terms, _member("David Mckinley", "David", "McKinley", "2014-03-07", "2022-09-21")
                      ).legislator.bioguide == "M001180"
        assert _match(index_and_terms, _member("Bill Pascrell", "Bill", "Pascrell", "2019-08-27", "2021-12-20")
                      ).legislator.bioguide == "P000096"
        assert _match(index_and_terms, _member("Beto O'Rourke", "Beto", "O'Rourke", "2013-01-15", "2014-12-19")
                      ).legislator.bioguide == "O000170"

    def test_compound_surname_last_word(self, index_and_terms):
        r = _match(index_and_terms, _member("Cathy Rodgers", "Cathy", "Rodgers", "2022-12-02", "2023-05-12"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "M001159"
        r = _match(index_and_terms, _member("Matthew Epps", "Matthew", "Epps", "2026-06-16", "2026-06-16"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "V000139"

    def test_party_follows_mid_term_switch(self, index_and_terms):
        r = _match(index_and_terms, _member("Justin Amash", "Justin", "Amash", "2015-11-10", "2020-03-18"))
        assert r.status == STATUS_MATCHED
        assert r.term.party == "I"            # independent on 2020-03-18
        r = _match(index_and_terms, _member("Justin Amash", "Justin", "Amash", "2015-11-10", "2018-06-01"))
        assert r.term.party == "R"

    def test_ambiguous_same_surname_same_window(self, index_and_terms):
        r = _match(index_and_terms, _member("John Smith", "John", "Smith", "2018-01-01", "2019-01-01"))
        assert r.status == STATUS_AMBIGUOUS
        assert {c.bioguide for c in r.candidates} == {"S900001", "S900002"}

    def test_window_disambiguates_same_surname(self, index_and_terms):
        r = _match(index_and_terms, _member("John Smith", "John", "Smith", "2015-06-01", "2016-06-01"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "S900001"

    def test_middle_initial_does_not_shadow_strong_match(self, index_and_terms):
        r = _match(index_and_terms, _member("Dan Bishop", "Dan", "Bishop", "2022-11-28", "2023-10-26"))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "B001311"

    def test_prefix_holding_real_first_name(self, index_and_terms):
        index, raw = index_and_terms
        r = match_member(_member("J. Hill", "J.", "Hill", "2016-01-01", "2020-01-01", prefix="James"), index,
                         raw_terms=raw)
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "H001072"

    def test_surname_only_is_review_not_matched(self, index_and_terms):
        r = _match(index_and_terms, _member("Armstrong Armstrong", "Armstrong", "Armstrong",
                                            "2026-03-24", "2026-08-20", prefix=None))
        assert r.status == STATUS_REVIEW and r.legislator.bioguide == "A000383"
        assert "parser casualty" in r.reason
        r = _match(index_and_terms, _member("David Cawthorn", "David", "Cawthorn", "2021-09-24", "2022-05-18"))
        assert r.status == STATUS_REVIEW

    def test_unmatched(self, index_and_terms):
        assert _match(index_and_terms, _member("Neal Facs", "Neal", "FACS", "2020-08-07", "2024-11-06")
                      ).status == STATUS_UNMATCHED
        r = _match(index_and_terms, _member("Greg Gianforte", "Greg", "Gianforte", "1990-01-01", "1991-01-01"))
        assert r.status == STATUS_UNMATCHED

    def test_no_trades_uses_stock_act_window(self, index_and_terms):
        r = _match(index_and_terms, _member("Greg Gianforte", "Greg", "Gianforte", None, None, n=0))
        assert r.status == STATUS_MATCHED and r.legislator.bioguide == "G000584"


class TestBatchUniqueness:
    def test_existing_bioguide_becomes_duplicate(self, index_and_terms):
        index, raw = index_and_terms
        m = _member("James Hill", "James", "Hill", "2015-12-23", "2025-12-31")
        [r] = match_members([m], index, {"H001072": "J. French Hill"}, raw_terms=raw)
        assert r.status == STATUS_DUPLICATE and "J. French Hill" in r.reason

    def test_two_rows_same_bioguide_both_ambiguous(self, index_and_terms):
        index, raw = index_and_terms
        a = _member("Tom Rooney", "Tom", "Rooney", "2014-01-01", "2015-01-01")
        b = _member("Thomas Rooney", "Thomas", "Rooney", "2016-01-01", "2017-01-01")
        results = match_members([a, b], index, {}, raw_terms=raw)
        assert [r.status for r in results] == [STATUS_AMBIGUOUS, STATUS_AMBIGUOUS]
