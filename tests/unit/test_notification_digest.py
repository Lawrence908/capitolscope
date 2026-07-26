"""
Tests for the batched trade-alert digest formatting.

Covers the ORM-trade -> template-row conversion and the digest HTML/text
builders. No email is actually sent and no DB is touched.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.notifications.notification_service import NotificationService
from domains.notifications.templates import TradeAlertEmailTemplate

pytestmark = pytest.mark.unit


def _svc():
    # Bypass __init__ (which builds an EmailService); we only exercise pure helpers.
    return NotificationService.__new__(NotificationService)


def _trade(**kw):
    defaults = dict(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        member=SimpleNamespace(display_name="Rep. Jane Doe", full_name="Jane Doe"),
        ticker="AAPL",
        asset_name="Apple Inc.",
        transaction_type="P",
        transaction_date=date(2026, 1, 15),
        amount_exact=None,
        amount_min=100_00,
        amount_max=250_00,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestActionMapping:
    def test_purchase_sale_exchange(self):
        svc = _svc()
        assert svc._action(_trade(transaction_type="P"))[1] == "Purchase"
        assert svc._action(_trade(transaction_type="S"))[1] == "Sale"
        assert svc._action(_trade(transaction_type="E"))[1] == "Exchange"

    def test_unknown_transaction_type_falls_back(self):
        emoji, label = _svc()._action(_trade(transaction_type="X"))
        assert emoji == "⚪"
        assert label == "X"


class TestAmountFormatting:
    def test_exact_amount(self):
        assert _svc()._format_orm_amount(_trade(amount_exact=1_234_00)) == "$1,234"

    def test_range_amount(self):
        assert _svc()._format_orm_amount(_trade(amount_exact=None, amount_min=100_00, amount_max=250_00)) == "$100 - $250"

    def test_missing_amount(self):
        t = _trade(amount_exact=None, amount_min=None, amount_max=None)
        assert _svc()._format_orm_amount(t) == "Amount not specified"


class TestDigestItem:
    def test_prefers_member_display_name(self):
        rule = SimpleNamespace(name="Watch Doe")
        item = _svc()._build_digest_item(_trade(), rule)
        assert item["member_name"] == "Rep. Jane Doe"
        assert item["ticker"] == "AAPL"
        assert item["action_text"] == "Purchase"
        assert item["reason"] == "Watch Doe"

    def test_falls_back_when_member_missing(self):
        rule = SimpleNamespace(name="r")
        item = _svc()._build_digest_item(_trade(member=None), rule)
        assert item["member_name"].startswith("Member ")


class TestDigestTemplate:
    def test_html_lists_all_members_and_trades(self):
        user = SimpleNamespace(first_name="Chris", email="chris@example.com")
        items = [
            {"member_name": "Rep. A", "ticker": "AAPL", "asset_name": "Apple",
             "action_emoji": "🟢", "action_text": "Purchase", "amount_str": "$100 - $250",
             "transaction_date": date(2026, 1, 15), "trade_id": "t1", "reason": "r"},
            {"member_name": "Rep. B", "ticker": "MSFT", "asset_name": "Microsoft",
             "action_emoji": "🔴", "action_text": "Sale", "amount_str": "$500",
             "transaction_date": date(2026, 1, 16), "trade_id": "t2", "reason": "r"},
        ]
        html = TradeAlertEmailTemplate().generate_trade_alert_digest_email(user, items)
        assert "Rep. A" in html and "Rep. B" in html
        assert "AAPL" in html and "MSFT" in html
        assert "Chris" in html  # greeting
        assert "2 new trade(s)" in html

    def test_text_fallback_lists_trades(self):
        svc = _svc()
        items = [
            {"member_name": "Rep. A", "ticker": "AAPL", "asset_name": "Apple",
             "action_text": "Purchase", "amount_str": "$100 - $250",
             "transaction_date": date(2026, 1, 15)},
        ]
        text = svc._generate_digest_text(items)
        assert "Rep. A" in text and "AAPL" in text and "Purchase" in text
