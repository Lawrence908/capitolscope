"""
Notification services for business logic and coordination.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from domains.notifications.crud import TradeAlertRuleCRUD, NotificationDeliveryCRUD
from domains.notifications.models import TradeAlertRule, NotificationDelivery
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service layer for notification operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_crud = TradeAlertRuleCRUD(session)
        self.delivery_crud = NotificationDeliveryCRUD(session)
    
    async def create_member_alert(self, user_id: str, member_id: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a member-specific trade alert with validation (member_id = UUID string)."""
        try:
            from uuid import UUID
            if not member_id or not str(member_id).strip():
                raise HTTPException(status_code=400, detail="Valid member ID is required")
            try:
                UUID(str(member_id).strip())
            except ValueError:
                raise HTTPException(status_code=400, detail="Member ID must be a valid UUID")

            alert_rule = await self.alert_crud.create_member_alert(
                user_id, str(member_id).strip(), alert_data
            )

            return {
                "alert_rule_id": alert_rule.id,
                "member_id": str(member_id).strip(),
                "alert_type": "member_trades",
                "created_at": alert_rule.created_at.isoformat(),
                "is_active": alert_rule.is_active
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating member alert: {e}")
            raise HTTPException(status_code=500, detail="Failed to create member alert")
    
    async def create_amount_alert(self, user_id: str, threshold: float, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an amount threshold alert with validation."""
        try:
            # Validate threshold
            if not threshold or threshold <= 0:
                raise HTTPException(status_code=400, detail="Valid threshold amount is required")
            
            # Create the alert rule
            alert_rule = await self.alert_crud.create_amount_alert(user_id, threshold, alert_data)
            
            # Return formatted response
            return {
                "alert_rule_id": alert_rule.id,
                "threshold": threshold,
                "alert_type": "amount_threshold",
                "created_at": alert_rule.created_at.isoformat(),
                "is_active": alert_rule.is_active
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating amount alert: {e}")
            raise HTTPException(status_code=500, detail="Failed to create amount alert")
    
    async def create_ticker_alert(self, user_id: str, ticker: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a ticker-specific alert with validation."""
        try:
            # Validate ticker
            ticker_upper = ticker.upper().strip()
            if not ticker_upper or len(ticker_upper) > 10:
                raise HTTPException(status_code=400, detail="Valid ticker symbol is required")
            
            # Create the alert rule
            alert_rule = await self.alert_crud.create_ticker_alert(user_id, ticker_upper, alert_data)
            
            # Return formatted response
            return {
                "alert_rule_id": alert_rule.id,
                "ticker": ticker_upper,
                "alert_type": "ticker_trades",
                "created_at": alert_rule.created_at.isoformat(),
                "is_active": alert_rule.is_active
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating ticker alert: {e}")
            raise HTTPException(status_code=500, detail="Failed to create ticker alert")
    
    async def get_user_alert_rules(
        self, 
        user_id: str, 
        alert_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get user's alert rules with pagination info."""
        try:
            # Get alert rules
            alert_rules = await self.alert_crud.get_user_alert_rules(
                user_id, alert_type, is_active, skip, limit
            )
            
            # Get total count
            total_count = await self.alert_crud.count_user_alert_rules(user_id)
            
            # Convert to response format
            rule_data = []
            for rule in alert_rules:
                cond = rule.conditions if isinstance(rule.conditions, dict) else {}
                mem_uuid = str(rule.target_member_id) if rule.target_member_id else cond.get("member_uuid")
                rule_dict = {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "alert_type": rule.alert_type,
                    "target_id": rule.target_id,
                    "target_member_id": mem_uuid,
                    "target_symbol": rule.target_symbol,
                    "target_name": rule.target_name,
                    "threshold_value": rule.threshold_value / 100 if rule.threshold_value else None,
                    "notification_channels": rule.notification_channels,
                    "is_active": rule.is_active,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat()
                }
                rule_data.append(rule_dict)
            
            return rule_data, total_count
            
        except Exception as e:
            logger.error(f"Error retrieving alert rules: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve alert rules")
    
    async def update_alert_rule(
        self, 
        rule_id: int, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an alert rule with validation."""
        try:
            # Convert threshold to cents if provided
            if "threshold_value" in update_data and update_data["threshold_value"]:
                update_data["threshold_value"] = int(update_data["threshold_value"] * 100)
            
            # Update the rule
            updated_rule = await self.alert_crud.update_alert_rule(rule_id, user_id, update_data)
            
            if not updated_rule:
                raise HTTPException(status_code=404, detail="Alert rule not found")
            
            # Return formatted response
            return {
                "alert_rule_id": updated_rule.id,
                "name": updated_rule.name,
                "alert_type": updated_rule.alert_type,
                "is_active": updated_rule.is_active,
                "updated_at": updated_rule.updated_at.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating alert rule: {e}")
            raise HTTPException(status_code=500, detail="Failed to update alert rule")
    
    async def delete_alert_rule(self, rule_id: int, user_id: str) -> Dict[str, bool]:
        """Delete an alert rule with validation."""
        try:
            # Delete the rule
            deleted = await self.alert_crud.delete_alert_rule(rule_id, user_id)
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Alert rule not found")
            
            # Return formatted response
            return {
                "deleted": True,
                "alert_rule_id": rule_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting alert rule: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete alert rule")
    
    async def get_delivery_history(
        self,
        user_id: str,
        days: int = 7,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[NotificationDelivery]:
        """Get notification delivery history for a user."""
        try:
            return await self.delivery_crud.get_delivery_history(user_id, days, status, skip, limit)
        except Exception as e:
            logger.error(f"Error retrieving delivery history: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve delivery history")

    async def get_alert_stats(self, user_id: str) -> Dict[str, Any]:
        """Dashboard stats: active alerts, notifications today, total triggered, delivery rate."""
        try:
            active = await self.alert_crud.count_active_alert_rules(user_id)
            stats = await self.delivery_crud.get_delivery_stats(user_id)

            attempted = stats["sent"] + stats["failed"]
            delivery_rate = round(stats["sent"] / attempted * 100, 1) if attempted else 100.0

            return {
                "active_alerts": active,
                "notifications_today": stats["today"],
                "total_triggered": stats["total"],
                "delivery_rate": delivery_rate,
            }
        except Exception as e:
            logger.error(f"Error retrieving alert stats: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve alert stats")

    async def get_alert_notifications(
        self,
        user_id: str,
        days: int = 7,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Delivery history mapped to the frontend notification shape (with trade details)."""
        try:
            deliveries = await self.delivery_crud.get_delivery_history(
                user_id, days, status, skip, limit
            )

            type_labels = {"P": "Purchase", "S": "Sale", "E": "Exchange"}
            items: List[Dict[str, Any]] = []
            for d in deliveries:
                trade = d.trade
                rule = d.alert_rule
                member = getattr(trade, "member", None) if trade else None

                amount_cents = None
                if trade is not None:
                    amount_cents = trade.amount_exact or trade.amount_max or trade.amount_min

                items.append({
                    "id": str(d.id),
                    "alert_id": str(d.alert_rule_id),
                    "alert_name": getattr(rule, "name", None) or "Trade alert",
                    "alert_type": getattr(rule, "alert_type", None),
                    "triggered_at": d.created_at.isoformat() if d.created_at else None,
                    "trade_details": {
                        "member_name": (
                            getattr(member, "display_name", None)
                            or getattr(member, "full_name", None)
                            or "Unknown member"
                        ),
                        "ticker": getattr(trade, "ticker", None),
                        "amount": (amount_cents / 100) if amount_cents else None,
                        "transaction_type": type_labels.get(
                            getattr(trade, "transaction_type", None), None
                        ),
                    },
                    "delivery_status": d.delivery_status,
                    "delivery_method": "email",
                    "error_message": d.error_message,
                })
            return items
        except Exception as e:
            logger.error(f"Error retrieving alert notifications: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve alert notifications")