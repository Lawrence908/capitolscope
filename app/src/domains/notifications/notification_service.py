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



