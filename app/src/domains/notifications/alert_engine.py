"""
Alert Rule Engine for Congressional Trade Notifications.

This engine evaluates alert rules against new trades to determine which users should be notified.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """Engine for evaluating alert rules against trades."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def evaluate_all_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Evaluate all types of alerts for a trade."""
        triggered_alerts = []
        
        # Member-specific alerts
        member_alerts = await self.evaluate_member_alerts(trade)
        triggered_alerts.extend(member_alerts)
        
        # Amount-based alerts
        amount_alerts = await self.evaluate_amount_alerts(trade)
        triggered_alerts.extend(amount_alerts)
        
        # Ticker-specific alerts
        ticker_alerts = await self.evaluate_ticker_alerts(trade)
        triggered_alerts.extend(ticker_alerts)
        
        # Remove duplicates (same user, same alert type)
        unique_alerts = self._deduplicate_alerts(triggered_alerts)
        
        logger.info(f"Trade {trade.id}: {len(unique_alerts)} unique alerts triggered")
        return unique_alerts
    
    async def evaluate_member_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users watching this specific congress member."""
        try:
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "member_trades",
                    TradeAlertRule.target_id == trade.member_id,
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} member alerts for member {trade.member_id}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating member alerts: {e}")
            return []
    
    async def evaluate_amount_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users with amount-based alerts that should trigger."""
        try:
            # Get trade amount (use max amount if range)
            trade_amount = trade.amount_max or trade.amount_exact or 0
            
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "amount_threshold",
                    TradeAlertRule.threshold_value <= trade_amount,
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} amount alerts for trade amount {trade_amount}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating amount alerts: {e}")
            return []
    
    async def evaluate_ticker_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users watching this specific ticker."""
        if not trade.ticker:
            return []
        
        try:
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "ticker_trades",
                    TradeAlertRule.target_symbol == trade.ticker.upper(),
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} ticker alerts for {trade.ticker}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating ticker alerts: {e}")
            return []
    
    def _deduplicate_alerts(self, alerts: List[TradeAlertRule]) -> List[TradeAlertRule]:
        """Remove duplicate alerts for the same user and alert type."""
        seen = set()
        unique_alerts = []
        
        for alert in alerts:
            key = (alert.user_id, alert.alert_type, alert.target_id)
            if key not in seen:
                seen.add(key)
                unique_alerts.append(alert)
        
        return unique_alerts



