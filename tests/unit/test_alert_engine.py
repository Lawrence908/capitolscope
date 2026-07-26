"""
Tests for the trade AlertRuleEngine matching + dedup logic.

Regression focus: member_trades alerts must match on the ``target_member_id``
UUID column (not the legacy integer ``target_id``), which is the bug that made
member alerts silently never fire. See migration b3d9f0a1c2e4.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

# Import the schemas package first to avoid a circular-import ordering issue
# when alert_engine is the first notifications module loaded.
import schemas  # noqa: F401

# Register all domain models so ORM query compilation can resolve relationships
# (mirrors what alembic/env.py imports).
from sqlalchemy.orm import configure_mappers
from domains.securities import models as _securities_models  # noqa: F401
from domains.congressional import models as _congressional_models  # noqa: F401
from domains.users import models as _users_models  # noqa: F401
from domains.notifications import models as _notifications_models  # noqa: F401
from domains.portfolio import models as _portfolio_models  # noqa: F401

configure_mappers()

from domains.notifications.alert_engine import AlertRuleEngine

pytestmark = pytest.mark.unit


def _rule(**kw):
    """A lightweight stand-in for a TradeAlertRule row.

    The engine only reads attributes off the rule, so we avoid instantiating the
    mapped ORM class (which would require the full model registry to be
    configured) and use a namespace with the fields dedup/matching touch.
    """
    defaults = dict(
        user_id=None,
        alert_type=None,
        target_member_id=None,
        target_symbol=None,
        threshold_value=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _mock_session_returning(rules):
    """An AsyncSession whose execute() yields the given rules and records the query."""
    session = AsyncMock()
    captured = {}

    async def _execute(query):
        captured["query"] = query
        result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rules))
        return result

    session.execute.side_effect = _execute
    return session, captured


class TestMemberAlertMatching:
    @pytest.mark.asyncio
    async def test_member_query_filters_on_target_member_id(self):
        member_id = uuid.uuid4()
        session, captured = _mock_session_returning([])
        engine = AlertRuleEngine(session)
        trade = SimpleNamespace(member_id=member_id, ticker=None)

        await engine.evaluate_member_alerts(trade)

        sql = str(captured["query"].compile(compile_kwargs={"literal_binds": True}))
        # Match on the member UUID column in the WHERE clause...
        assert "trade_alert_rules.target_member_id =" in sql
        # ...and not on the legacy integer target_id column (the original bug).
        assert "trade_alert_rules.target_id =" not in sql

    @pytest.mark.asyncio
    async def test_returns_rules_from_session(self):
        member_id = uuid.uuid4()
        rule = _rule(
            user_id=uuid.uuid4(),
            alert_type="member_trades",
            target_member_id=member_id,
            name="Watch member",
        )
        session, _ = _mock_session_returning([rule])
        engine = AlertRuleEngine(session)
        trade = SimpleNamespace(member_id=member_id, ticker=None)

        result = await engine.evaluate_member_alerts(trade)
        assert result == [rule]


def _trade(member_id, ticker=None, amount_max=None, amount_exact=None):
    return SimpleNamespace(
        member_id=member_id,
        ticker=ticker,
        amount_max=amount_max,
        amount_exact=amount_exact,
    )


class TestBatchMatching:
    @pytest.mark.asyncio
    async def test_matches_member_ticker_and_amount_in_one_pass(self):
        member_a = uuid.uuid4()
        member_b = uuid.uuid4()
        user = uuid.uuid4()
        rules = [
            _rule(user_id=user, alert_type="member_trades", target_member_id=member_a),
            _rule(user_id=user, alert_type="ticker_trades", target_symbol="AAPL"),
            _rule(user_id=user, alert_type="amount_threshold", threshold_value=100_00),
        ]
        session, _ = _mock_session_returning(rules)
        engine = AlertRuleEngine(session)

        trades = [
            _trade(member_a, ticker="AAPL", amount_max=50_00),   # member + ticker (amount too small)
            _trade(member_b, ticker="MSFT", amount_exact=500_00),  # amount only
            _trade(member_b, ticker=None, amount_max=None),        # no match
        ]
        matches = await engine.match_trades_batch(trades)

        matched_rule_types = sorted(rule.alert_type for _, rule in matches)
        assert matched_rule_types == ["amount_threshold", "member_trades", "ticker_trades"]
        assert len(matches) == 3
        # The rules query is issued exactly once regardless of trade count.
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_inactive_rules_excluded_by_query(self):
        # match_trades_batch relies on the WHERE is_active clause; the mock only
        # returns active rules, so an empty rule set yields no matches.
        session, captured = _mock_session_returning([])
        engine = AlertRuleEngine(session)
        matches = await engine.match_trades_batch([_trade(uuid.uuid4(), ticker="AAPL")])
        assert matches == []
        sql = str(captured["query"].compile(compile_kwargs={"literal_binds": True}))
        assert "is_active" in sql

    @pytest.mark.asyncio
    async def test_ticker_match_is_case_insensitive(self):
        user = uuid.uuid4()
        rules = [_rule(user_id=user, alert_type="ticker_trades", target_symbol="aapl")]
        session, _ = _mock_session_returning(rules)
        engine = AlertRuleEngine(session)
        matches = await engine.match_trades_batch([_trade(uuid.uuid4(), ticker="AAPL")])
        assert len(matches) == 1


class TestDeduplication:
    def test_same_member_and_user_deduped(self):
        engine = AlertRuleEngine(AsyncMock())
        user_id = uuid.uuid4()
        member_id = uuid.uuid4()
        rules = [
            _rule(user_id=user_id, alert_type="member_trades", target_member_id=member_id),
            _rule(user_id=user_id, alert_type="member_trades", target_member_id=member_id),
        ]
        assert len(engine._deduplicate_alerts(rules)) == 1

    def test_different_members_not_deduped(self):
        engine = AlertRuleEngine(AsyncMock())
        user_id = uuid.uuid4()
        rules = [
            _rule(user_id=user_id, alert_type="member_trades", target_member_id=uuid.uuid4()),
            _rule(user_id=user_id, alert_type="member_trades", target_member_id=uuid.uuid4()),
        ]
        assert len(engine._deduplicate_alerts(rules)) == 2

    def test_different_tickers_not_deduped(self):
        engine = AlertRuleEngine(AsyncMock())
        user_id = uuid.uuid4()
        rules = [
            _rule(user_id=user_id, alert_type="ticker_trades", target_symbol="AAPL"),
            _rule(user_id=user_id, alert_type="ticker_trades", target_symbol="MSFT"),
        ]
        assert len(engine._deduplicate_alerts(rules)) == 2
