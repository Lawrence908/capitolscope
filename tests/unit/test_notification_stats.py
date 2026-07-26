"""
Tests for alert stats + notification-history mapping in the NotificationService
facade (domains.notifications.services). The CRUD layer is mocked so no DB is
touched; the focus is the delivery-rate math and the delivery -> frontend-shape
mapping.
"""

import uuid
from datetime import datetime, date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.notifications.services import NotificationService

pytestmark = pytest.mark.unit


def _service():
    svc = NotificationService(MagicMock())
    svc.alert_crud = AsyncMock()
    svc.delivery_crud = AsyncMock()
    return svc


class TestAlertStats:
    @pytest.mark.asyncio
    async def test_delivery_rate_is_100_when_nothing_attempted(self):
        svc = _service()
        svc.alert_crud.count_active_alert_rules.return_value = 3
        svc.delivery_crud.get_delivery_stats.return_value = {
            "total": 0, "today": 0, "sent": 0, "failed": 0
        }
        stats = await svc.get_alert_stats(uuid.uuid4())
        assert stats == {
            "active_alerts": 3,
            "notifications_today": 0,
            "total_triggered": 0,
            "delivery_rate": 100.0,
        }

    @pytest.mark.asyncio
    async def test_delivery_rate_computed_from_sent_and_failed(self):
        svc = _service()
        svc.alert_crud.count_active_alert_rules.return_value = 1
        svc.delivery_crud.get_delivery_stats.return_value = {
            "total": 12, "today": 4, "sent": 9, "failed": 1
        }
        stats = await svc.get_alert_stats(uuid.uuid4())
        assert stats["notifications_today"] == 4
        assert stats["total_triggered"] == 12
        assert stats["delivery_rate"] == 90.0  # 9 / (9+1)


class TestNotificationMapping:
    @pytest.mark.asyncio
    async def test_maps_delivery_to_frontend_shape(self):
        svc = _service()
        member = SimpleNamespace(display_name="Rep. Jane Doe", full_name="Jane Doe")
        trade = SimpleNamespace(
            ticker="AAPL", asset_name="Apple Inc.", transaction_type="P",
            amount_exact=None, amount_min=100_00, amount_max=250_00, member=member,
        )
        rule = SimpleNamespace(name="Watch Doe", alert_type="member_trades")
        delivery = SimpleNamespace(
            id=uuid.uuid4(), alert_rule_id=uuid.uuid4(),
            created_at=datetime(2026, 1, 15, 14, 30),
            delivery_status="sent", error_message=None, trade=trade, alert_rule=rule,
        )
        svc.delivery_crud.get_delivery_history.return_value = [delivery]

        items = await svc.get_alert_notifications(uuid.uuid4(), days=7)
        assert len(items) == 1
        item = items[0]
        assert item["alert_name"] == "Watch Doe"
        assert item["alert_type"] == "member_trades"
        assert item["delivery_status"] == "sent"
        assert item["delivery_method"] == "email"
        td = item["trade_details"]
        assert td["member_name"] == "Rep. Jane Doe"
        assert td["ticker"] == "AAPL"
        assert td["transaction_type"] == "Purchase"
        # amount is exposed in dollars (amount_exact None -> falls back to amount_max)
        assert td["amount"] == 250.0

    @pytest.mark.asyncio
    async def test_missing_trade_and_member_do_not_crash(self):
        svc = _service()
        delivery = SimpleNamespace(
            id=uuid.uuid4(), alert_rule_id=uuid.uuid4(),
            created_at=datetime(2026, 1, 15), delivery_status="sent",
            error_message=None, trade=None, alert_rule=None,
        )
        svc.delivery_crud.get_delivery_history.return_value = [delivery]
        items = await svc.get_alert_notifications(uuid.uuid4())
        td = items[0]["trade_details"]
        assert td["member_name"] == "Unknown member"
        assert td["ticker"] is None
        assert td["amount"] is None
        assert items[0]["alert_name"] == "Trade alert"
