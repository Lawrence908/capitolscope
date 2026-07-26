"""
Tests for the mirror-portfolio compute core (PriceBook, midpoint_dollars,
replay_positions, build_holdings) in domains.portfolio.mirror_service.

Pure/no-DB: these pin the shares-from-price reconstruction math.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.portfolio.mirror_service import (
    PriceBook, midpoint_dollars, replay_positions, build_holdings,
    compute_equity_series, _month_starts,
)

pytestmark = pytest.mark.unit


def _trade(sid, ttype, d, exact=None, lo=None, hi=None, ticker="AAPL"):
    return SimpleNamespace(
        security_id=sid, transaction_type=ttype, transaction_date=d,
        amount_exact=exact, amount_min=lo, amount_max=hi, ticker=ticker,
    )


class TestMidpointDollars:
    def test_exact_wins(self):
        assert midpoint_dollars(_trade("s", "P", date(2020, 1, 1), exact=5000_00)) == 5000.0

    def test_range_midpoint(self):
        assert midpoint_dollars(_trade("s", "P", date(2020, 1, 1), lo=1000_00, hi=15000_00)) == 8000.0

    def test_only_max(self):
        assert midpoint_dollars(_trade("s", "P", date(2020, 1, 1), hi=15000_00)) == 15000.0

    def test_none_is_zero(self):
        assert midpoint_dollars(_trade("s", "P", date(2020, 1, 1))) == 0.0


class TestPriceBook:
    def test_price_on_or_before_uses_prior_day(self):
        sid = uuid.uuid4()
        pb = PriceBook([
            (sid, date(2020, 1, 1), 100),
            (sid, date(2020, 1, 3), 110),
        ])
        assert pb.price_on_or_before(sid, date(2020, 1, 1)) == 100.0
        assert pb.price_on_or_before(sid, date(2020, 1, 2)) == 100.0  # falls back to prior
        assert pb.price_on_or_before(sid, date(2020, 1, 3)) == 110.0
        assert pb.price_on_or_before(sid, date(2019, 12, 31)) is None  # before first
        assert pb.latest(sid) == 110.0

    def test_unknown_security(self):
        pb = PriceBook([])
        assert pb.price_on_or_before(uuid.uuid4(), date(2020, 1, 1)) is None
        assert pb.latest(uuid.uuid4()) is None


class TestReplayAndValue:
    def test_single_buy_then_appreciation(self):
        sid = uuid.uuid4()
        # buy $10,000 when price is $100 -> 100 shares; latest price $150
        pb = PriceBook([
            (sid, date(2020, 1, 1), 100),
            (sid, date(2021, 1, 1), 150),
        ])
        trades = [_trade(sid, "P", date(2020, 1, 1), exact=10_000_00)]
        pos = replay_positions(trades, pb)
        assert pos[sid]["shares"] == pytest.approx(100.0)

        result = build_holdings(pos, pb, {sid: {"ticker": "AAPL", "name": "Apple"}})
        h = result["holdings"][0]
        assert h["shares"] == pytest.approx(100.0)
        assert h["market_value"] == pytest.approx(15_000.0)
        assert h["cost_basis"] == pytest.approx(10_000.0)
        assert h["unrealized_gain"] == pytest.approx(5_000.0)
        assert h["return_pct"] == pytest.approx(50.0)
        assert result["totals"]["return_pct"] == pytest.approx(50.0)

    def test_partial_sale_reduces_shares_and_cost(self):
        sid = uuid.uuid4()
        pb = PriceBook([
            (sid, date(2020, 1, 1), 100),   # buy day
            (sid, date(2020, 6, 1), 100),   # sell day (same price)
            (sid, date(2021, 1, 1), 100),   # latest
        ])
        trades = [
            _trade(sid, "P", date(2020, 1, 1), exact=10_000_00),  # 100 shares
            _trade(sid, "S", date(2020, 6, 1), exact=4_000_00),   # sell 40 shares
        ]
        pos = replay_positions(trades, pb)
        assert pos[sid]["shares"] == pytest.approx(60.0)
        assert pos[sid]["cost_basis"] == pytest.approx(6_000.0)

    def test_full_sale_closes_position_out_of_holdings(self):
        sid = uuid.uuid4()
        pb = PriceBook([
            (sid, date(2020, 1, 1), 100),
            (sid, date(2020, 6, 1), 100),
        ])
        trades = [
            _trade(sid, "P", date(2020, 1, 1), exact=5_000_00),  # 50 shares
            _trade(sid, "S", date(2020, 6, 1), exact=5_000_00),  # sell 50 shares
        ]
        result = build_holdings(replay_positions(trades, pb), pb, {})
        assert result["holdings"] == []
        assert result["totals"]["holdings_count"] == 0

    def test_sale_without_prior_holding_is_ignored(self):
        sid = uuid.uuid4()
        pb = PriceBook([(sid, date(2020, 1, 1), 100)])
        trades = [_trade(sid, "S", date(2020, 1, 1), exact=5_000_00)]
        pos = replay_positions(trades, pb)
        assert pos.get(sid, {"shares": 0})["shares"] == pytest.approx(0.0)

    def test_unpriced_trade_is_skipped(self):
        sid = uuid.uuid4()
        pb = PriceBook([])  # no prices at all
        trades = [_trade(sid, "P", date(2020, 1, 1), exact=10_000_00)]
        assert replay_positions(trades, pb) == {}

    def test_sector_allocation_weights(self):
        s1, s2 = uuid.uuid4(), uuid.uuid4()
        pb = PriceBook([
            (s1, date(2020, 1, 1), 100), (s1, date(2021, 1, 1), 100),  # $10k flat
            (s2, date(2020, 1, 1), 100), (s2, date(2021, 1, 1), 100),  # $30k flat
        ])
        trades = [
            _trade(s1, "P", date(2020, 1, 1), exact=10_000_00),
            _trade(s2, "P", date(2020, 1, 1), exact=30_000_00),
        ]
        meta = {
            s1: {"ticker": "A", "name": "A", "sector": "Technology"},
            s2: {"ticker": "B", "name": "B", "sector": "Financials"},
        }
        result = build_holdings(replay_positions(trades, pb), pb, meta)
        alloc = {a["sector"]: a["weight_pct"] for a in result["sector_allocation"]}
        assert alloc == {"Financials": 75.0, "Technology": 25.0}
        # largest sector first
        assert result["sector_allocation"][0]["sector"] == "Financials"

    @pytest.mark.asyncio
    async def test_compare_surfaces_overlap(self, monkeypatch):
        from domains.portfolio import mirror_service as ms

        canned = {
            "id1": {
                "holdings": [
                    {"security_id": "s1", "ticker": "AAPL", "name": "Apple", "market_value": 100.0},
                    {"security_id": "s2", "ticker": "MSFT", "name": "MS", "market_value": 50.0},
                ],
                "totals": {"market_value": 150.0, "holdings_count": 2},
                "sector_allocation": [],
            },
            "id2": {
                "holdings": [
                    {"security_id": "s2", "ticker": "MSFT", "name": "MS", "market_value": 80.0},
                    {"security_id": "s3", "ticker": "NVDA", "name": "NV", "market_value": 30.0},
                ],
                "totals": {"market_value": 110.0, "holdings_count": 2},
                "sector_allocation": [],
            },
        }

        async def fake_reconstruct(session, ids):
            return canned[ids[0]]

        monkeypatch.setattr(ms, "reconstruct_holdings", fake_reconstruct)
        result = await ms.compare_member_holdings(None, ["id1", "id2"])

        assert len(result["members"]) == 2
        # Only MSFT (s2) is held by both.
        assert result["overlap"]["count"] == 1
        common = result["overlap"]["common_securities"][0]
        assert common["ticker"] == "MSFT"
        assert sorted(common["held_by"]) == ["id1", "id2"]
        assert common["combined_value"] == 130.0

    def test_missing_sector_defaults_to_unknown(self):
        sid = uuid.uuid4()
        pb = PriceBook([(sid, date(2020, 1, 1), 100), (sid, date(2021, 1, 1), 100)])
        trades = [_trade(sid, "P", date(2020, 1, 1), exact=10_000_00)]
        result = build_holdings(replay_positions(trades, pb), pb, {})  # no meta
        assert result["holdings"][0]["sector"] == "Unknown"
        assert result["sector_allocation"][0]["sector"] == "Unknown"

    def test_two_securities_roll_up_totals(self):
        s1, s2 = uuid.uuid4(), uuid.uuid4()
        pb = PriceBook([
            (s1, date(2020, 1, 1), 100), (s1, date(2021, 1, 1), 200),  # 2x
            (s2, date(2020, 1, 1), 100), (s2, date(2021, 1, 1), 100),  # flat
        ])
        trades = [
            _trade(s1, "P", date(2020, 1, 1), exact=10_000_00, ticker="A"),
            _trade(s2, "P", date(2020, 1, 1), exact=10_000_00, ticker="B"),
        ]
        result = build_holdings(
            replay_positions(trades, pb), pb,
            {s1: {"ticker": "A", "name": "A"}, s2: {"ticker": "B", "name": "B"}},
        )
        t = result["totals"]
        assert t["cost_basis"] == pytest.approx(20_000.0)
        assert t["market_value"] == pytest.approx(30_000.0)  # 20k + 10k
        assert t["return_pct"] == pytest.approx(50.0)
        # sorted by market value desc -> the 2x security first
        assert result["holdings"][0]["ticker"] == "A"


class TestEquityCurve:
    def test_month_starts_includes_end(self):
        dates = _month_starts(date(2020, 1, 15), date(2020, 3, 20))
        assert dates[0] == date(2020, 1, 1)
        assert dates[-1] == date(2020, 3, 20)  # explicit end point appended

    def test_portfolio_and_spy_driven_by_same_cashflow(self):
        s1 = uuid.uuid4()
        spy = uuid.uuid4()
        pb = PriceBook([
            (s1, date(2020, 1, 1), 100), (s1, date(2021, 1, 1), 200),   # 2x
            (spy, date(2020, 1, 1), 50), (spy, date(2021, 1, 1), 100),  # 2x
        ])
        # Buy $10k of s1 -> 100 shares; the same $10k buys 200 SPY shares.
        trades = [_trade(s1, "P", date(2020, 1, 1), exact=10_000_00)]
        series = compute_equity_series(trades, pb, spy, [date(2020, 1, 1), date(2021, 1, 1)])
        assert series[0]["portfolio_value"] == pytest.approx(10_000)
        assert series[0]["spy_value"] == pytest.approx(10_000)
        assert series[-1]["portfolio_value"] == pytest.approx(20_000)
        assert series[-1]["spy_value"] == pytest.approx(20_000)

    def test_outperformance_when_holding_beats_spy(self):
        s1 = uuid.uuid4()
        spy = uuid.uuid4()
        pb = PriceBook([
            (s1, date(2020, 1, 1), 100), (s1, date(2021, 1, 1), 400),   # 4x
            (spy, date(2020, 1, 1), 100), (spy, date(2021, 1, 1), 200),  # 2x
        ])
        trades = [_trade(s1, "P", date(2020, 1, 1), exact=10_000_00)]
        series = compute_equity_series(trades, pb, spy, [date(2020, 1, 1), date(2021, 1, 1)])
        assert series[-1]["portfolio_value"] == pytest.approx(40_000)
        assert series[-1]["spy_value"] == pytest.approx(20_000)

    def test_no_spy_yields_none_benchmark(self):
        s1 = uuid.uuid4()
        pb = PriceBook([(s1, date(2020, 1, 1), 100), (s1, date(2021, 1, 1), 200)])
        trades = [_trade(s1, "P", date(2020, 1, 1), exact=10_000_00)]
        series = compute_equity_series(trades, pb, None, [date(2021, 1, 1)])
        assert series[-1]["portfolio_value"] == pytest.approx(20_000)
        assert series[-1]["spy_value"] is None
