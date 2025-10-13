"""
Trade Detection Service for Congressional Trade Notifications.

This service detects new congressional trades and triggers notification processing.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from domains.congressional.models import CongressionalTrade
from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.alert_engine import AlertRuleEngine
from domains.notifications.notification_service import NotificationService
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class TradeDetectionService:
    """Service for detecting new trades and triggering notifications."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_engine = AlertRuleEngine(session)
        self.notification_service = NotificationService(session)
    
    async def detect_new_trades(self, since_date: datetime) -> List[CongressionalTradeDetail]:
        """Find all new trades since a given date."""
        try:
            query = select(CongressionalTrade).where(
                CongressionalTrade.created_at >= since_date
            ).order_by(CongressionalTrade.created_at.desc())
            
            result = await self.session.execute(query)
            trades = result.scalars().all()
            
            logger.info(f"Detected {len(trades)} new trades since {since_date}")
            return [CongressionalTradeDetail.from_orm(trade) for trade in trades]
            
        except Exception as e:
            logger.error(f"Error detecting new trades: {e}")
            raise
    
    async def process_new_trade(self, trade: CongressionalTradeDetail) -> Dict[str, Any]:
        """Process a single new trade and trigger notifications."""
        try:
            logger.info(f"Processing new trade: {trade.id} for member {trade.member_id}")
            
            # Step 1: Evaluate alert rules
            triggered_alerts = await self.alert_engine.evaluate_all_alerts(trade)
            
            # Step 2: Send notifications
            notifications_sent = 0
            for alert_rule in triggered_alerts:
                try:
                    await self.notification_service.send_trade_alert_email(
                        alert_rule.user, trade, alert_rule
                    )
                    notifications_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send notification for alert {alert_rule.id}: {e}")
            
            logger.info(f"Trade {trade.id} processed: {notifications_sent} notifications sent")
            
            return {
                "trade_id": trade.id,
                "member_id": trade.member_id,
                "alerts_triggered": len(triggered_alerts),
                "notifications_sent": notifications_sent
            }
            
        except Exception as e:
            logger.error(f"Error processing trade {trade.id}: {e}")
            raise
    
    async def batch_process_trades(self, trades: List[CongressionalTradeDetail]) -> Dict[str, Any]:
        """Process multiple trades efficiently."""
        results = {
            "total_trades": len(trades),
            "processed_trades": 0,
            "total_notifications": 0,
            "errors": []
        }
        
        for trade in trades:
            try:
                result = await self.process_new_trade(trade)
                results["processed_trades"] += 1
                results["total_notifications"] += result["notifications_sent"]
            except Exception as e:
                results["errors"].append({
                    "trade_id": trade.id,
                    "error": str(e)
                })
                logger.error(f"Error processing trade {trade.id}: {e}")
        
        logger.info(f"Batch processing completed: {results}")
        return results



