"""
Pure-function tests for the anonymous public feed (api.public): lag and
lateness rules, compact money labels, factual headline builders, notable-card
selection and late-filer grouping. No DB.
"""

from datetime import date

import pytest

from api import public as pub

pytestmark = pytest.mark.unit


def _trade(i, member="m1", name="Tommy Tuberville", lag=10, status="N", amin=100100, amax=1500000,
           ttype="P", ticker="INTC", tdate="2024-05-07", ndate="2026-08-05"):
    return {
        "id": f"t{i}", "member_id": member, "member_name": name, "member_party": "R",
        "member_state": "AL", "member_chamber": "Senate", "member_district": None,
        "ticker": ticker, "asset_name": "Intel Corp", "transaction_type": ttype,
        "transaction_date": tdate, "notification_date": ndate,
        "amount_min": amin, "amount_max": amax, "filing_status": status,
        "days_to_disclose": lag,
    }


class TestLag:
    def test_lag_days(self):
        assert pub.lag_days(date(2026, 1, 1), date(2026, 1, 31)) == 30
        assert pub.lag_days(date(2026, 1, 1), date(2026, 1, 1)) == 0

    def test_lag_none_for_missing_or_negative(self):
        assert pub.lag_days(None, date(2026, 1, 1)) is None
        assert pub.lag_days(date(2026, 2, 1), date(2026, 1, 1)) is None

    def test_is_late_boundary(self):
        assert pub.is_late(45, "N") is False  # exactly the limit is on time
        assert pub.is_late(46, "N") is True
        assert pub.is_late(46, None) is True

    def test_amendments_never_late(self):
        assert pub.is_late(400, "A") is False
        assert pub.is_late(400, "a") is False


class TestMoney:
    @pytest.mark.parametrize("cents,label", [
        (50000100, "$500K"),
        (100000000, "$1M"),
        (250000000, "$2.5M"),
        (1500100, "$15K"),
        (100100, "$1K"),
        (50000, "$500"),
        (None, ""),
    ])
    def test_short_money(self, cents, label):
        assert pub.short_money(cents) == label

    def test_bracket_phrase(self):
        assert pub.bracket_phrase(50000100, 100000000) == "the $500K to $1M range"
        assert pub.bracket_phrase(5000000000, None) == "the range above $50M"
        assert pub.bracket_phrase(None, None) == "an undisclosed amount"
        assert pub.bracket_phrase(100000, 100000) == "an amount of $1K"


class TestHeadlines:
    def test_surname_drops_suffix(self):
        assert pub.surname("Tommy Tuberville") == "Tuberville"
        assert pub.surname("Donald S. Beyer Jr.") == "Beyer"
        assert pub.surname("") == "A member"

    def test_asset_label(self):
        assert pub.asset_label("INTC", "Intel") == "INTC"
        assert pub.asset_label(None, "Greenbrier Affiliates : Greenbrier Fund LP") == "Greenbrier Affiliates"
        assert pub.asset_label(None, None) == "an undisclosed asset"
        assert pub.asset_label(None, "x" * 80).endswith("...")

    def test_late_headline(self):
        h = pub.headline_late(_trade(1, lag=820))
        assert h == "Tuberville discloses May 2024 INTC purchase, 775 days past the deadline"

    def test_bracket_headline(self):
        h = pub.headline_bracket(_trade(1, name="Sheri Biggs", amin=50000100, amax=100000000, ticker="BNS"))
        assert h == "Biggs buys BNS in the $500K to $1M range"

    def test_sell_and_exchange_verbs(self):
        assert pub.trade_verb("S") == "sells"
        assert pub.trade_verb("S", noun=True) == "sale"
        assert pub.trade_verb("E") == "exchanges"
        assert pub.trade_verb(None) == "reports"

    def test_committee_headline(self):
        h = pub.headline_committee(_trade(1, name="Gilbert Ray Cisneros", ticker="MOG.A"),
                                   "House Committee on Armed Services", "Industrials")
        assert h == "Cisneros buys MOG.A, an Industrials company, while on the Armed Services Committee"

    def test_no_emdash_in_headlines(self):
        t = _trade(1, lag=900)
        for h in (pub.headline_late(t), pub.headline_bracket(t),
                  pub.headline_committee(t, "Senate Committee on Banking", "Financials")):
            assert "—" not in h


class TestCommittee:
    def test_committee_short(self):
        assert pub.committee_short("House Committee on Armed Services") == "Armed Services"
        assert pub.committee_short("Senate Committee on the Budget") == "Budget"
        assert pub.committee_short("Permanent Subcommittee") == "Permanent Subcommittee"

    def test_matched_committee(self):
        cs = ["House Committee on Appropriations", "House Committee on Armed Services"]
        assert pub.matched_committee(cs, "Industrials") == "House Committee on Armed Services"
        assert pub.matched_committee(cs, "Health Care") is None
        assert pub.matched_committee(None, "Industrials") is None
        assert pub.matched_committee(cs, None) is None


class TestPickNotable:
    def test_order_and_distinct_members(self):
        late = [_trade(1, member="a", lag=800)]
        brackets = [
            _trade(1, member="a", amax=500),  # same trade as late: skipped
            _trade(2, member="a", amax=400),  # same member as late: skipped first pass
            _trade(3, member="b", amax=300),
            _trade(4, member="c", amax=200),
        ]
        committee = [dict(_trade(5, member="d"), _committee="Armed Services", _sector="Industrials")]
        cards = pub.pick_notable(late, brackets, committee)
        assert [c["kind"] for c in cards] == ["late", "bracket", "bracket", "committee"]
        assert [c["trade"]["id"] for c in cards] == ["t1", "t3", "t4", "t5"]
        # private keys stripped
        assert "_committee" not in cards[-1]["trade"]
        assert cards[-1]["committee"] == "Armed Services"

    def test_fills_with_brackets_when_no_late_or_committee(self):
        brackets = [_trade(i, member=f"m{i}") for i in range(6)]
        cards = pub.pick_notable([], brackets, [])
        assert len(cards) == 4
        assert all(c["kind"] == "bracket" for c in cards)

    def test_falls_back_to_same_member_when_needed(self):
        brackets = [_trade(i, member="solo") for i in range(3)]
        cards = pub.pick_notable([], brackets, [])
        assert len(cards) == 3

    def test_empty(self):
        assert pub.pick_notable([], [], []) == []


class TestGroupLateFilers:
    def test_grouping_counts_and_ranking(self):
        trades = [
            _trade(1, member="a", name="A One", lag=100, ndate="2026-03-01"),
            _trade(2, member="a", name="A One", lag=300, ndate="2026-05-01"),
            _trade(3, member="a", name="A One", lag=60, ndate="2026-01-01"),
            _trade(4, member="b", name="B Two", lag=900),
            _trade(5, member="b", name="B Two", lag=900, status="A"),  # amendment dropped
            _trade(6, member="c", name="C Three", lag=20),  # on time dropped
        ]
        out = pub.group_late_filers(trades, {"a": 10, "b": 4})
        assert [g["member_id"] for g in out] == ["a", "b"]
        a = out[0]
        assert a["late_count"] == 3
        assert a["worst_days"] == 300
        assert a["median_days"] == 100
        assert a["filings_in_window"] == 10
        assert a["latest_late_filing"] == "2026-05-01"
        assert [t["id"] for t in a["trades"]] == ["t2", "t1", "t3"]  # worst lag first
        assert out[1]["late_count"] == 1

    def test_per_member_cap(self):
        trades = [_trade(i, member="a", lag=50 + i) for i in range(10)]
        out = pub.group_late_filers(trades, per_member=3)
        assert out[0]["late_count"] == 10
        assert len(out[0]["trades"]) == 3
        assert out[0]["filings_in_window"] is None
