"""
Trade Alert Notification Service for Congressional Trade Notifications.

This service handles sending and tracking trade alert notifications.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule, NotificationDelivery
from domains.notifications.templates import TradeAlertEmailTemplate
from domains.users.models import User
from core.email import EmailService

import logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending and tracking notifications."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_service = EmailService()
        self.email_template = TradeAlertEmailTemplate()
    
    async def send_trade_alert_email(
        self, 
        user: User, 
        trade: CongressionalTradeDetail, 
        alert_rule: TradeAlertRule
    ) -> bool:
        """Send trade alert email to user."""
        try:
            # Generate email content
            subject = self._generate_email_subject(trade, alert_rule)
            html_content = self.email_template.generate_trade_alert_email(trade, user, alert_rule)
            text_content = self._generate_text_content(trade, alert_rule)
            
            # Send email
            success = await self.email_service._send_email(
                to_email=user.email,
                to_name=user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            # Track delivery
            await self._track_delivery(user.id, trade.id, alert_rule.id, success)
            
            if success:
                logger.info(f"Trade alert email sent to {user.email} for trade {trade.id}")
            else:
                logger.error(f"Failed to send trade alert email to {user.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trade alert email to {user.email}: {e}")
            await self._track_delivery(user.id, trade.id, alert_rule.id, False, str(e))
            return False
    
    async def send_trade_alert_digest(
        self,
        user: User,
        matches: List[tuple],
    ) -> bool:
        """Send a single digest email to a user for many (trade, rule) matches.

        Records one NotificationDelivery per (trade, rule) so the same match is
        never emailed twice on a later run. ``matches`` is a list of
        ``(trade, rule)`` tuples where ``trade`` is an ORM row (with ``member``
        loaded) and ``rule`` is a TradeAlertRule.
        """
        if not matches:
            return True

        items = [self._build_digest_item(trade, rule) for trade, rule in matches]
        subject = f"🚨 {len(items)} new congressional trade(s) matched your alerts"
        html_content = self.email_template.generate_trade_alert_digest_email(user, items)
        text_content = self._generate_digest_text(items)

        success = False
        try:
            success = await self.email_service._send_email(
                to_email=user.email,
                to_name=user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending digest to {user.email}: {e}")
            success = False

        # Only record deliveries on success so a failed digest is retried on the
        # next run rather than being permanently suppressed by the dedup filter.
        if success:
            title, message, members, tickers = self._digest_summary(items)
            await self._create_inapp_notification(user.id, title, message, len(items), members, tickers)
            await self._bulk_track_delivery(user.id, matches)      # commits in-app + deliveries
            await self._dispatch_extra_channels(user, title, message)  # push / SMS (Pro+)
            logger.info(f"Digest with {len(items)} trades sent to {user.email}")
        else:
            logger.error(f"Failed to send digest to {user.email}; will retry next run")
        return success

    @staticmethod
    def _digest_summary(items: List[Dict[str, Any]]) -> tuple:
        """Build the short title/message shared by in-app, push, and SMS."""
        members = list(dict.fromkeys(it["member_name"] for it in items))  # ordered-unique
        tickers = [it["ticker"] for it in items if it.get("ticker")]
        member_summary = ", ".join(members[:3]) + ("…" if len(members) > 3 else "")
        title = f"{len(items)} new congressional trade(s) matched your alerts"
        message = f"{len(members)} member(s) you follow: {member_summary}"
        return title, message, members, tickers

    async def _create_inapp_notification(
        self, user_id, title: str, message: str, count: int, members: List[str], tickers: List[str]
    ) -> None:
        """Add an in-app (bell) notification, batched into the delivery commit."""
        try:
            from domains.notifications.inapp_service import InAppNotificationService

            await InAppNotificationService(self.session).create(
                user_id,
                title=title,
                message=message,
                notification_type="TRADE_ALERT",
                priority="high" if count >= 10 else "normal",
                extra_data={"count": count, "members": members, "tickers": tickers[:20]},
                commit=False,
            )
        except Exception as e:
            logger.error(f"Failed to create in-app notification for {user_id}: {e}")

    async def _dispatch_extra_channels(self, user, title: str, message: str) -> None:
        """Fan out to web push / SMS for Pro+ users who enabled them (no-op otherwise)."""
        try:
            from sqlalchemy import select
            from domains.notifications.models import NotificationSubscription
            from domains.notifications.channels import ChannelDispatcher

            sub = (await self.session.execute(
                select(NotificationSubscription).where(NotificationSubscription.user_id == user.id)
            )).scalar_one_or_none()
            if sub is None:
                return  # no subscription -> no extra channels enabled
            await ChannelDispatcher(self.session).dispatch(user, sub, title, message)
        except Exception as e:
            logger.error(f"Extra-channel dispatch failed for {user.id}: {e}")

    def _build_digest_item(self, trade, rule) -> Dict[str, Any]:
        """Build a template row dict from an ORM trade + the rule that matched it."""
        action_emoji, action_text = self._action(trade)
        member = getattr(trade, "member", None)
        member_name = (
            getattr(member, "display_name", None)
            or getattr(member, "full_name", None)
            or f"Member {trade.member_id}"
        )
        return {
            "member_name": member_name,
            "ticker": trade.ticker,
            "asset_name": trade.asset_name,
            "action_emoji": action_emoji,
            "action_text": action_text,
            "amount_str": self._format_orm_amount(trade),
            "transaction_date": trade.transaction_date,
            "trade_id": str(trade.id),
            "reason": rule.name,
        }

    @staticmethod
    def _action(trade) -> tuple:
        """Map the single-char transaction_type (P/S/E) to (emoji, label)."""
        mapping = {
            "P": ("🟢", "Purchase"),
            "S": ("🔴", "Sale"),
            "E": ("🔄", "Exchange"),
        }
        return mapping.get((trade.transaction_type or "").upper(), ("⚪", trade.transaction_type or "Trade"))

    @staticmethod
    def _format_orm_amount(trade) -> str:
        """Format an ORM trade's amount (cents) for display."""
        if trade.amount_exact:
            return f"${trade.amount_exact / 100:,.0f}"
        if trade.amount_min and trade.amount_max:
            return f"${trade.amount_min / 100:,.0f} - ${trade.amount_max / 100:,.0f}"
        return "Amount not specified"

    def _generate_digest_text(self, items: List[Dict[str, Any]]) -> str:
        """Plain-text fallback for the digest email."""
        lines = ["New congressional trades matched your alerts:", ""]
        for it in items:
            sym = it["ticker"] or it["asset_name"] or "Unknown"
            lines.append(
                f"- {it['member_name']}: {it['action_text']} {sym} "
                f"({it['amount_str']}) on {it['transaction_date'] or 'Unknown'}"
            )
        lines += ["", "Manage alerts: https://capitolscope.chrislawrence.ca/alerts"]
        return "\n".join(lines)

    async def _bulk_track_delivery(self, user_id, matches: List[tuple]) -> None:
        """Record one sent NotificationDelivery per (trade, rule) in a single commit."""
        try:
            now = datetime.utcnow()
            for trade, rule in matches:
                self.session.add(
                    NotificationDelivery(
                        user_id=user_id,
                        trade_id=trade.id,
                        alert_rule_id=rule.id,
                        delivery_status="sent",
                        sent_at=now,
                    )
                )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error bulk-tracking {len(matches)} deliveries: {e}")

    async def send_bulk_alerts(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Send multiple notifications efficiently."""
        results = {
            "total": len(notifications),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for notification in notifications:
            try:
                success = await self.send_trade_alert_email(
                    notification["user"],
                    notification["trade"],
                    notification["alert_rule"]
                )
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
                logger.error(f"Error in bulk notification: {e}")
        
        logger.info(f"Bulk notification completed: {results}")
        return results
    
    def _generate_email_subject(self, trade: CongressionalTradeDetail, alert_rule: TradeAlertRule) -> str:
        """Generate email subject line."""
        member_name = trade.member_name or f"Member {trade.member_id}"
        
        if alert_rule.alert_type == "member_trades":
            return f"🚨 {member_name} Made a New Trade"
        elif alert_rule.alert_type == "amount_threshold":
            return f"💰 Large Trade Alert: {member_name}"
        elif alert_rule.alert_type == "ticker_trades":
            return f"📈 {trade.ticker} Trade Alert: {member_name}"
        else:
            return f"📊 New Congressional Trade Alert"
    
    def _generate_text_content(self, trade: CongressionalTradeDetail, alert_rule: TradeAlertRule) -> str:
        """Generate plain text email content."""
        member_name = trade.member_name or f"Member {trade.member_id}"
        amount_str = self._format_amount(trade)
        
        return f"""
New Congressional Trade Alert

Member: {member_name}
Stock: {trade.ticker or 'Unknown'} - {trade.asset_name or 'Unknown Asset'}
Action: {trade.transaction_type or 'Unknown'}
Amount: {amount_str}
Date: {trade.transaction_date or 'Unknown'}

View full details: https://capitolscope.chrislawrence.ca/trade/{trade.id}

Unsubscribe: https://capitolscope.chrislawrence.ca/unsubscribe
        """.strip()
    
    def _format_amount(self, trade: CongressionalTradeDetail) -> str:
        """Format trade amount for display."""
        if trade.amount_exact:
            return f"${trade.amount_exact / 100:,.2f}"
        elif trade.amount_min and trade.amount_max:
            return f"${trade.amount_min / 100:,.2f} - ${trade.amount_max / 100:,.2f}"
        else:
            return "Amount not specified"
    
    async def _track_delivery(
        self, 
        user_id: int, 
        trade_id: int, 
        alert_rule_id: int, 
        success: bool, 
        error_message: Optional[str] = None
    ):
        """Track notification delivery status."""
        try:
            delivery = NotificationDelivery(
                user_id=user_id,
                trade_id=trade_id,
                alert_rule_id=alert_rule_id,
                delivery_status="sent" if success else "failed",
                sent_at=datetime.utcnow(),
                error_message=error_message
            )
            
            self.session.add(delivery)
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error tracking delivery: {e}")



