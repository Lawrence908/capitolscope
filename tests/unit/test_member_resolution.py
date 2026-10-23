"""Filer -> legislator resolution, using the real misattributions found in prod."""

from datetime import date

import pytest

from domains.congressional.member_enrichment import Legislator, LegislatorIndex, Term
from domains.congressional.member_resolution import (
    Filer,
    chamber_from_doc_id,
    identity_fields,
    name_tokens,
    parse_state_dst,
    resolve_filer,
)

pytestmark = pytest.mark.unit


def leg(bio, first, last, terms, middle=None, nickname=None, current=False):
    return Legislator(bio, first, last, middle, nickname, None, None, tuple(terms), current)


def term(chamber, state, start, end, district=None, party="R"):
    return Term(chamber, date.fromisoformat(start), date.fromisoformat(end), state, district, party, party)


INDEX = LegislatorIndex([
    leg("S000510", "Adam", "Smith", [term("House", "WA", "1997-01-03", "2027-01-03", "9", "D")], current=True),
    leg("S000583", "Lamar", "Smith", [term("House", "TX", "1987-01-06", "2019-01-03", "21")]),
    leg("T000250", "John", "Thune", [term("Senate", "SD", "2005-01-04", "2029-01-03")], current=True),
    leg("B000589", "John", "Boehner", [term("House", "OH", "1991-01-03", "2015-11-01", "8")], middle="A."),
    leg("L000600", "Laurel", "Lee", [term("House", "FL", "2023-01-03", "2027-01-03", "15")], middle="M.", current=True),
    leg("L000590", "Susie", "Lee", [term("House", "NV", "2019-01-03", "2027-01-03", "3", "D")], current=True),
    leg("N000188", "Alan", "Nunnelee", [term("House", "MS", "2011-01-05", "2015-02-06", "1")]),
    leg("D000628", "Neal", "Dunn", [term("House", "FL", "2017-01-03", "2027-01-03", "2")], middle="P.", current=True),
    leg("A000383", "Alan", "Armstrong", [term("Senate", "OK", "2026-03-24", "2027-01-03")], current=True),
    leg("H001091", "Ashley", "Hinson", [term("House", "IA", "2021-01-03", "2027-01-03", "1")], current=True),
    leg("M001243", "David", "McCormick", [term("Senate", "PA", "2025-01-03", "2031-01-03")], current=True),
    leg("C001127", "Sheila", "Cherfilus-McCormick", [term("House", "FL", "2022-01-18", "2027-01-03", "20", "D")], current=True),
])


def resolve(**kw):
    return resolve_filer(Filer(**kw), INDEX)


def test_same_surname_disambiguated_by_state():
    r = resolve(first="Lamar", last="Smith", state="TX", chamber="House", on=date(2016, 5, 1))
    assert r.status == "matched" and r.legislator.bioguide == "S000583"


def test_first_name_alone_never_matches_a_different_surname():
    # The old matcher put Boehner's filings on Sen. John Thune.
    r = resolve(first="John A.", last="Boehner", state="OH", chamber="House", on=date(2014, 6, 1))
    assert r.legislator.bioguide == "B000589"


def test_substring_surname_does_not_match():
    # "Lee" is inside "Nunnelee"; the old matcher confused them.
    r = resolve(first="Laurel Mrs", last="Lee", state="FL", chamber="House", on=date(2024, 3, 1))
    assert r.legislator.bioguide == "L000600"


def test_credentials_in_first_name_are_ignored():
    r = resolve(first="Neal Patrick MD, FACS", last="Dunn", state="FL", chamber="House", on=date(2020, 1, 1))
    assert r.legislator.bioguide == "D000628"


def test_senate_filer_without_prefix():
    # "Alan Armstrong" with no prefix produced the garbled "Armstrong Armstrong".
    r = resolve(first="Alan", last="Armstrong", chamber="Senate", on=date(2026, 7, 21))
    assert r.legislator.bioguide == "A000383"


def test_married_compound_surname():
    r = resolve(first="Ashley", last="Hinson Arenholz", state="IA", chamber="House", on=date(2023, 2, 1))
    assert r.legislator.bioguide == "H001091"


def test_chamber_separates_hyphenated_namesake():
    r = resolve(first="David H", last="McCormick", chamber="Senate", on=date(2025, 6, 1))
    assert r.legislator.bioguide == "M001243"


def test_no_state_no_given_name_match_is_not_guessed():
    r = resolve(first="Zed", last="Smith", chamber="House", on=date(2016, 5, 1))
    assert r.status in ("ambiguous", "unmatched") and r.legislator is None


def test_unknown_surname_unmatched():
    assert resolve(first="Jane", last="Nobody", state="CA", chamber="House", on=date(2020, 1, 1)).status == "unmatched"


@pytest.mark.parametrize("raw,expected", [("LA05", ("LA", "5")), ("AK00", ("AK", None)), ("VT", ("VT", None)), ("", (None, None))])
def test_parse_state_dst(raw, expected):
    assert parse_state_dst(raw) == expected


def test_chamber_from_doc_id():
    assert chamber_from_doc_id("20035691") == "House"
    assert chamber_from_doc_id("fda235b3-bad7-4637-8fa1-053f354d929c") == "Senate"
    assert chamber_from_doc_id("unknown_3") is None


def test_name_tokens_drop_honorifics_and_credentials():
    assert name_tokens("Hon. Neal Patrick MD, FACS") == ["neal", "patrick"]


def test_identity_fields_use_term_in_force():
    f = identity_fields(INDEX.by_bioguide["L000600"], date(2024, 3, 1))
    assert (f["bioguide_id"], f["chamber"], f["state"], f["district"], f["party"]) == ("L000600", "House", "FL", "15", "R")
    assert f["term_end"] is None  # current member
