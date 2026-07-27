"""
Notification subscription service (async).

Backs the notification-preferences UI and supplies per-user delivery cadence to
the digest task. Cadence lives in ``NotificationSubscription.email_frequency``
and is normalized to one of: instant, daily, weekly.

Behavior note: a user with NO subscription row defaults to ``instant`` (this
preserves the pre-4b behavior where every match was sent on the 10-minute beat).
Rows created through this service default to ``instant`` too, overriding the
model column's legacy ``daily`` default.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

VALID_CADENCES = ("instant", "daily", "weekly")


def normalize_cadence(freq: Optional[str]) -> str:
    return freq if freq in VALID_CADENCES else "instant"


def serialize_subscription(sub) -> Dict[str, Any]:
    return {
        "email_enabled": sub.email_enabled,
        "push_enabled": sub.push_enabled,
        "sms_enabled": sub.sms_enabled,
        "trade_alerts": sub.trade_alerts,
        "portfolio_updates": sub.portfolio_updates,
        "market_alerts": sub.market_alerts,
        "newsletter": sub.newsletter,
        "email_frequency": normalize_cadence(sub.email_frequency),
        "alert_threshold": sub.alert_threshold,
    }


class SubscriptionService:
    """Async CRUD for NotificationSubscription + cadence lookup."""

    _UPDATABLE = {
        "email_enabled", "push_enabled", "sms_enabled", "trade_alerts",
        "portfolio_updates", "market_alerts", "newsletter",
        "email_frequency", "alert_threshold",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id):
        from domains.notifications.models import NotificationSubscription

        sub = (await self.session.execute(
            select(NotificationSubscription).where(NotificationSubscription.user_id == user_id)
        )).scalar_one_or_none()
        if sub is None:
            # Default new rows to instant to match the app's historical behavior.
            sub = NotificationSubscription(user_id=user_id, email_frequency="instant")
            self.session.add(sub)
            await self.session.commit()
            await self.session.refresh(sub)
        return sub

    async def update(self, user_id, data: Dict[str, Any]):
        sub = await self.get_or_create(user_id)
        if "email_frequency" in data:
            data["email_frequency"] = normalize_cadence(data["email_frequency"])
        for field, value in data.items():
            if field in self._UPDATABLE and value is not None:
                setattr(sub, field, value)
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def get_cadences(self, user_ids: List) -> Dict[Any, str]:
        """Map each user_id to its cadence WITHOUT creating rows (missing -> instant)."""
        from domains.notifications.models import NotificationSubscription

        if not user_ids:
            return {}
        rows = (await self.session.execute(
            select(NotificationSubscription.user_id, NotificationSubscription.email_frequency)
            .where(NotificationSubscription.user_id.in_(user_ids))
        )).all()
        # Key by str() so callers can pass UUID objects or strings interchangeably.
        found = {str(r.user_id): normalize_cadence(r.email_frequency) for r in rows}
        return {uid: found.get(str(uid), "instant") for uid in user_ids}
