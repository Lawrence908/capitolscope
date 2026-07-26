"""
CRUD operations for Trade Alert Rules and Notification management.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from domains.notifications.models import TradeAlertRule, NotificationDelivery
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class NotificationCRUD:
    """CRUD operations for notifications."""
    
    def __init__(self):
        logger.info("NotificationCRUD initialized")
    
    async def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user notification subscriptions."""
        # TODO: Implement database query
        logger.info(f"Getting subscriptions for user {user_id}")
        return []
    
    async def create_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification subscription."""
        # TODO: Implement database insert
        logger.info(f"Creating subscription for user {user_id}")
        return {"id": 1, "user_id": user_id}
    
    async def update_subscription(self, subscription_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a notification subscription."""
        # TODO: Implement database update
        logger.info(f"Updating subscription {subscription_id}")
        return True
        
    async def delete_subscription(self, subscription_id: int) -> bool:
        """Delete a notification subscription."""
        # TODO: Implement database delete
        logger.info(f"Deleting subscription {subscription_id}")
        return True


# Export the CRUD class
__all__ = ["NotificationCRUD"]
class TradeAlertRuleCRUD:
    """CRUD operations for TradeAlertRule."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_alert_rule(self, user_id: str, rule_data: Dict[str, Any]) -> TradeAlertRule:
        """Create a new trade alert rule."""
        try:
            alert_rule = TradeAlertRule(
                user_id=user_id,
                name=rule_data.get("name"),
                description=rule_data.get("description"),
                alert_type=rule_data.get("alert_type"),
                target_id=rule_data.get("target_id"),
                target_member_id=rule_data.get("target_member_id"),
                target_symbol=rule_data.get("target_symbol"),
                target_name=rule_data.get("target_name"),
                threshold_value=rule_data.get("threshold_value"),
                conditions=rule_data.get("conditions"),
                notification_channels=rule_data.get("notification_channels", ["email"]),
                is_active=rule_data.get("is_active", True)
            )
            
            self.session.add(alert_rule)
            await self.session.commit()
            await self.session.refresh(alert_rule)
            
            logger.info(f"Created alert rule {alert_rule.id} for user {user_id}")
            return alert_rule
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating alert rule: {e}")
            raise
    
    async def create_member_alert(self, user_id: str, member_id: str, alert_data: Dict[str, Any]) -> TradeAlertRule:
        """Create a member-specific trade alert rule (member_id is congress member UUID string)."""
        rule_data = {
            "name": alert_data.get("name", "Member trade alerts"),
            "description": alert_data.get("description", "Get notified when this member makes trades"),
            "alert_type": "member_trades",
            "target_id": None,
            "target_member_id": member_id,
            "target_name": alert_data.get("member_name"),
            "conditions": {"member_uuid": member_id},
            "notification_channels": alert_data.get("notification_channels", ["email"]),
            "is_active": alert_data.get("is_active", True)
        }
        return await self.create_alert_rule(user_id, rule_data)
    
    async def create_amount_alert(self, user_id: str, threshold: float, alert_data: Dict[str, Any]) -> TradeAlertRule:
        """Create an amount threshold alert rule."""
        # Convert threshold to cents for storage
        threshold_cents = int(threshold * 100)
        
        rule_data = {
            "name": alert_data.get("name", f"Trades over ${threshold:,.2f}"),
            "description": alert_data.get("description", f"Get notified of all trades over ${threshold:,.2f}"),
            "alert_type": "amount_threshold",
            "threshold_value": threshold_cents,
            "notification_channels": alert_data.get("notification_channels", ["email"]),
            "is_active": alert_data.get("is_active", True)
        }
        return await self.create_alert_rule(user_id, rule_data)
    
    async def create_ticker_alert(self, user_id: str, ticker: str, alert_data: Dict[str, Any]) -> TradeAlertRule:
        """Create a ticker-specific trade alert rule."""
        ticker_upper = ticker.upper().strip()
        
        rule_data = {
            "name": alert_data.get("name", f"{ticker_upper} Trade Alerts"),
            "description": alert_data.get("description", f"Get notified when any member trades {ticker_upper}"),
            "alert_type": "ticker_trades",
            "target_symbol": ticker_upper,
            "target_name": alert_data.get("company_name"),
            "notification_channels": alert_data.get("notification_channels", ["email"]),
            "is_active": alert_data.get("is_active", True)
        }
        return await self.create_alert_rule(user_id, rule_data)
    
    async def get_user_alert_rules(
        self, 
        user_id: str, 
        alert_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[TradeAlertRule]:
        """Get alert rules for a user with optional filtering."""
        try:
            query = select(TradeAlertRule).where(TradeAlertRule.user_id == user_id)
            
            if alert_type:
                query = query.where(TradeAlertRule.alert_type == alert_type)
            
            if is_active is not None:
                query = query.where(TradeAlertRule.is_active == is_active)
            
            query = query.order_by(desc(TradeAlertRule.created_at)).offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            rules = result.scalars().all()
            
            logger.debug(f"Retrieved {len(rules)} alert rules for user {user_id}")
            return rules
            
        except Exception as e:
            logger.error(f"Error retrieving alert rules: {e}")
            raise
    
    async def get_alert_rule_by_id(self, rule_id: int, user_id: str) -> Optional[TradeAlertRule]:
        """Get a specific alert rule by ID, ensuring it belongs to the user."""
        try:
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.id == rule_id,
                    TradeAlertRule.user_id == user_id
                )
            )
            
            result = await self.session.execute(query)
            rule = result.scalar_one_or_none()
            
            return rule
            
        except Exception as e:
            logger.error(f"Error retrieving alert rule {rule_id}: {e}")
            raise
    
    async def update_alert_rule(
        self, 
        rule_id: int, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[TradeAlertRule]:
        """Update an alert rule."""
        try:
            rule = await self.get_alert_rule_by_id(rule_id, user_id)
            if not rule:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(rule, field):
                    setattr(rule, field, value)
            
            await self.session.commit()
            await self.session.refresh(rule)
            
            logger.info(f"Updated alert rule {rule_id} for user {user_id}")
            return rule
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating alert rule {rule_id}: {e}")
            raise
    
    async def delete_alert_rule(self, rule_id: int, user_id: str) -> bool:
        """Delete an alert rule."""
        try:
            rule = await self.get_alert_rule_by_id(rule_id, user_id)
            if not rule:
                return False
            
            await self.session.delete(rule)
            await self.session.commit()
            
            logger.info(f"Deleted alert rule {rule_id} for user {user_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            raise
    
    async def count_user_alert_rules(self, user_id: str) -> int:
        """Count total alert rules for a user."""
        try:
            query = select(TradeAlertRule).where(TradeAlertRule.user_id == user_id)
            result = await self.session.execute(query)
            count = len(result.scalars().all())
            return count

        except Exception as e:
            logger.error(f"Error counting alert rules: {e}")
            return 0

    async def count_active_alert_rules(self, user_id: str) -> int:
        """Count active alert rules for a user."""
        try:
            from sqlalchemy import func
            query = select(func.count()).select_from(TradeAlertRule).where(
                and_(
                    TradeAlertRule.user_id == user_id,
                    TradeAlertRule.is_active == True,
                )
            )
            result = await self.session.execute(query)
            return int(result.scalar() or 0)
        except Exception as e:
            logger.error(f"Error counting active alert rules: {e}")
            return 0


class NotificationDeliveryCRUD:
    """CRUD operations for NotificationDelivery."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_delivery_history(
        self,
        user_id: str,
        days: int = 7,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[NotificationDelivery]:
        """Get notification delivery history for a user.

        Eager-loads the related trade (and its member) and the alert rule so the
        API layer can render trade details without N+1 queries.
        """
        try:
            from datetime import datetime, timedelta
            # Imported lazily to avoid a circular import at module load time
            # (congressional.models -> ... -> notifications.crud).
            from domains.congressional.models import CongressionalTrade
            since_date = datetime.utcnow() - timedelta(days=days)

            conditions = [
                NotificationDelivery.user_id == user_id,
                NotificationDelivery.created_at >= since_date,
            ]
            if status and status != "all":
                conditions.append(NotificationDelivery.delivery_status == status)

            query = (
                select(NotificationDelivery)
                .where(and_(*conditions))
                .options(
                    selectinload(NotificationDelivery.trade).selectinload(CongressionalTrade.member),
                    selectinload(NotificationDelivery.alert_rule),
                )
                .order_by(desc(NotificationDelivery.created_at))
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)
            deliveries = result.scalars().all()

            logger.debug(f"Retrieved {len(deliveries)} delivery records for user {user_id}")
            return deliveries

        except Exception as e:
            logger.error(f"Error retrieving delivery history: {e}")
            raise

    async def get_delivery_stats(self, user_id: str) -> Dict[str, int]:
        """Aggregate delivery counts for a user: today, total, sent, failed."""
        try:
            from datetime import datetime, timezone
            from sqlalchemy import func

            start_of_today = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            row = (
                await self.session.execute(
                    select(
                        func.count().label("total"),
                        func.count()
                        .filter(NotificationDelivery.created_at >= start_of_today)
                        .label("today"),
                        func.count()
                        .filter(NotificationDelivery.delivery_status == "sent")
                        .label("sent"),
                        func.count()
                        .filter(NotificationDelivery.delivery_status == "failed")
                        .label("failed"),
                    ).where(NotificationDelivery.user_id == user_id)
                )
            ).one()

            return {
                "total": int(row.total or 0),
                "today": int(row.today or 0),
                "sent": int(row.sent or 0),
                "failed": int(row.failed or 0),
            }
        except Exception as e:
            logger.error(f"Error retrieving delivery stats: {e}")
            return {"total": 0, "today": 0, "sent": 0, "failed": 0}