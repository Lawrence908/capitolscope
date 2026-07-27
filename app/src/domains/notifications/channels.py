"""
Multichannel notification dispatch: web push (VAPID) + SMS (Twilio).

This is the readiness layer for Phase 4c. Channels fire only when ALL of the
following hold, and otherwise no-op silently (mirroring the email SMTP fallback):
  * the user's subscription has the channel enabled (push_enabled / sms_enabled)
  * the user is Pro+ (push/SMS are gated features)
  * the channel is configured (VAPID / Twilio creds present in settings)
  * the required library is installed (pywebpush / twilio)

Live delivery additionally needs a frontend service worker (to create push
subscriptions) and a user phone number for SMS — both tracked as follow-ups.
"""

import asyncio
import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from pywebpush import webpush, WebPushException  # type: ignore
    _PYWEBPUSH = True
except ImportError:  # pragma: no cover - optional dep
    _PYWEBPUSH = False

try:
    from twilio.rest import Client as _TwilioClient  # type: ignore
    _TWILIO = True
except ImportError:  # pragma: no cover - optional dep
    _TWILIO = False


async def register_push_subscription(
    session: AsyncSession, user_id, endpoint: str, p256dh: str, auth: str, user_agent: Optional[str] = None
):
    """Upsert a Web Push subscription for a user's device (keyed by endpoint)."""
    from domains.notifications.models import PushSubscription

    existing = (await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )).scalar_one_or_none()
    if existing:
        existing.user_id = user_id
        existing.p256dh_key = p256dh
        existing.auth_key = auth
        existing.user_agent = user_agent
        existing.is_active = True
        sub = existing
    else:
        sub = PushSubscription(
            user_id=user_id, endpoint=endpoint, p256dh_key=p256dh,
            auth_key=auth, user_agent=user_agent, is_active=True,
        )
        session.add(sub)
    await session.commit()
    return sub


async def unregister_push_subscription(session: AsyncSession, user_id, endpoint: str) -> bool:
    from domains.notifications.models import PushSubscription

    result = await session.execute(
        update(PushSubscription)
        .where(PushSubscription.endpoint == endpoint, PushSubscription.user_id == user_id)
        .values(is_active=False)
    )
    await session.commit()
    return result.rowcount > 0


class ChannelDispatcher:
    """Routes a notification to a user's enabled + permitted + configured channels."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def dispatch(self, user, subscription, title: str, message: str) -> dict:
        """Send push/SMS for one user. Returns a per-channel status dict."""
        result = {"push": "skipped", "sms": "skipped"}
        if not getattr(user, "is_premium", False):
            return result  # push/SMS are Pro+ only

        if getattr(subscription, "push_enabled", False):
            result["push"] = await self._maybe_push(user, title, message)
        if getattr(subscription, "sms_enabled", False):
            result["sms"] = await self._maybe_sms(user, message)
        return result

    async def _maybe_push(self, user, title: str, message: str) -> str:
        if not settings.push_configured:
            return "unconfigured"
        if not _PYWEBPUSH:
            return "lib_missing"

        from domains.notifications.models import PushSubscription

        subs = (await self.session.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user.id, PushSubscription.is_active == True  # noqa: E712
            )
        )).scalars().all()
        if not subs:
            return "no_devices"

        sent = 0
        for s in subs:
            try:
                await asyncio.to_thread(self._send_webpush, s, title, message)
                sent += 1
            except Exception as e:  # pragma: no cover - network
                logger.warning(f"Web push to {s.endpoint[:40]}… failed: {e}")
        return f"sent:{sent}"

    def _send_webpush(self, sub, title: str, message: str):  # pragma: no cover - needs creds
        import json
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
            },
            data=json.dumps({"title": title, "body": message}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY.get_secret_value(),
            vapid_claims={"sub": settings.VAPID_SUBJECT},
        )

    async def _maybe_sms(self, user, message: str) -> str:
        if not settings.sms_configured:
            return "unconfigured"
        if not _TWILIO:
            return "lib_missing"
        phone = getattr(user, "phone", None) or getattr(user, "phone_number", None)
        if not phone:
            return "no_phone"
        try:
            await asyncio.to_thread(self._send_sms, phone, message)
            return "sent"
        except Exception as e:  # pragma: no cover - network
            logger.warning(f"SMS to {phone} failed: {e}")
            return "error"

    def _send_sms(self, phone: str, message: str):  # pragma: no cover - needs creds
        client = _TwilioClient(
            settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN.get_secret_value()
        )
        client.messages.create(body=message[:1500], from_=settings.TWILIO_FROM_NUMBER, to=phone)
