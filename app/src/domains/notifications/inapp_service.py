"""
In-app notification service (async).

Backs the notification "bell" / inbox. Writes and reads the ``user_notifications``
table directly with the async session — the legacy ``UserNotificationRepository``
is sync (``self.db.query(...)``) and can't be used from the async API path.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _serialize(n) -> Dict[str, Any]:
    return {
        "id": str(n.id),
        "title": n.title,
        "message": n.message,
        "type": n.notification_type.value if n.notification_type else None,
        "priority": n.priority,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "extra_data": n.extra_data or {},
    }


class InAppNotificationService:
    """Async CRUD for the in-app notification inbox."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id,
        title: str,
        message: str,
        *,
        notification_type: str = "TRADE_ALERT",
        priority: str = "normal",
        extra_data: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ):
        """Create an IN_APP notification. Set commit=False to batch with a caller's transaction."""
        from domains.users.models import UserNotification, NotificationType, NotificationChannel

        notif = UserNotification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType(notification_type),
            channel=NotificationChannel.IN_APP,
            priority=priority,
            is_read=False,
            sent_at=datetime.now(timezone.utc),
            delivery_status="delivered",
            extra_data=extra_data or {},
        )
        self.session.add(notif)
        if commit:
            await self.session.commit()
        return notif

    async def list(
        self, user_id, unread_only: bool = False, skip: int = 0, limit: int = 20
    ) -> Dict[str, Any]:
        from domains.users.models import UserNotification

        conditions = [UserNotification.user_id == user_id]
        if unread_only:
            conditions.append(UserNotification.is_read == False)  # noqa: E712

        total = (await self.session.execute(
            select(func.count()).select_from(UserNotification).where(and_(*conditions))
        )).scalar() or 0

        rows = (await self.session.execute(
            select(UserNotification)
            .where(and_(*conditions))
            .order_by(UserNotification.created_at.desc())
            .offset(skip).limit(limit)
        )).scalars().all()

        unread = await self.unread_count(user_id)
        return {"items": [_serialize(n) for n in rows], "total": int(total), "unread": unread}

    async def unread_count(self, user_id) -> int:
        from domains.users.models import UserNotification

        return int((await self.session.execute(
            select(func.count()).select_from(UserNotification).where(
                and_(UserNotification.user_id == user_id, UserNotification.is_read == False)  # noqa: E712
            )
        )).scalar() or 0)

    async def mark_read(self, user_id, notification_id) -> bool:
        """Mark one notification read (scoped to the owner)."""
        from domains.users.models import UserNotification

        result = await self.session.execute(
            update(UserNotification)
            .where(and_(
                UserNotification.id == notification_id,
                UserNotification.user_id == user_id,
            ))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.session.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id) -> int:
        from domains.users.models import UserNotification

        result = await self.session.execute(
            update(UserNotification)
            .where(and_(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False,  # noqa: E712
            ))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.session.commit()
        return result.rowcount
