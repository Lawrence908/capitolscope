"""
Notifications API endpoints.

Supports CAP-14: Email Newsletter Infrastructure & CAP-15: Trade Alert System
Provides email notifications, trade alerts, and subscription management.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
import logging
logger = logging.getLogger(__name__)
from core.responses import success_response, error_response, paginated_response
from core.auth import get_current_user_optional, get_current_active_user, require_subscription, require_admin
from domains.users.models import User
from schemas.base import ResponseEnvelope, PaginatedResponse, PaginationMeta, create_response
from domains.notifications.schemas import (
    UserSubscriptionResponse, SubscriptionUpdateResponse, AlertListResponse, AlertResponse,
    AlertHistoryResponse, AlertHistoryItem, NewsletterOptionsResponse, NewsletterSubscription, 
    NewsletterUnsubscribeResponse, TemplateListResponse, DeliveryStatusResponse, TestNotificationResponse, 
    NotificationAnalyticsResponse, NotificationTemplate, SubscriptionPreferences, AlertConfiguration,
    AlertType, DeliveryStatus, NotificationType
)
from domains.notifications.models import TradeAlertRule, NotificationDelivery
from domains.notifications.services import NotificationService

router = APIRouter()


@router.get(
    "/subscriptions",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "User subscriptions retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_user_subscriptions(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get the user's notification preferences (channels + digest cadence).

    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting user subscriptions: user_id={current_user.id}")
    from domains.notifications.subscription_service import SubscriptionService, serialize_subscription

    sub = await SubscriptionService(session).get_or_create(current_user.id)
    return create_response(data=serialize_subscription(sub))


@router.put(
    "/subscriptions",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Subscription preferences updated successfully"},
        400: {"description": "Invalid preferences"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def update_user_subscriptions(
    session: AsyncSession = Depends(get_db_session),
    preferences: Dict[str, Any] = Body(..., description="Notification preferences"),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Update the user's notification preferences. ``email_frequency`` accepts
    instant / daily / weekly (the digest cadence).

    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Updating user subscriptions: user_id={current_user.id}, preferences={preferences}")
    from domains.notifications.subscription_service import SubscriptionService, serialize_subscription

    sub = await SubscriptionService(session).update(current_user.id, dict(preferences))
    return create_response(data=serialize_subscription(sub))


@router.get(
    "/alerts",
    response_model=ResponseEnvelope[PaginatedResponse[AlertResponse]],
    responses={
        200: {"description": "User alerts retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_user_alerts(
    session: AsyncSession = Depends(get_db_session),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[AlertResponse]]:
    """
    Get user's configured trade alerts.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting user alerts: user_id={current_user.id}, alert_type={alert_type}, "
               f"is_active={is_active}, skip={skip}, limit={limit}")
    
    # TODO: Implement user alerts retrieval
    
    # Create sample alert for demonstration
    alert_config = AlertConfiguration(
        alert_type=AlertType.TRADE_VOLUME,
        symbol="AAPL",
        threshold=1000.0,
        condition="above",
        is_active=True,
        notification_channels=["email"],
        description="High volume alert"
    )
    
    sample_alert = AlertResponse(
        alert_id=12345,
        user_id=current_user.id,
        alert_data=alert_config,
        created_at=datetime.utcnow(),
        is_active=True
    )
    
    alerts = [sample_alert] if is_active else []
    
    # Create pagination meta
    pagination_meta = PaginationMeta(
        page=1,
        per_page=limit,
        total=len(alerts),
        pages=1,
        has_next=False,
        has_prev=False
    )
    
    paginated_data = PaginatedResponse(
        items=alerts,
        meta=pagination_meta
    )
    
    return create_response(data=paginated_data)


@router.post(
    "/alerts",
    response_model=ResponseEnvelope[AlertResponse],
    responses={
        200: {"description": "Trade alert created successfully"},
        400: {"description": "Invalid alert configuration"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def create_alert(
    session: AsyncSession = Depends(get_db_session),
    alert_data: Dict[str, Any] = Body(..., description="Alert configuration"),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[AlertResponse]:
    """
    Create a new trade alert for the user.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Creating alert: user_id={current_user.id}, alert_data={alert_data}")
    
    # TODO: Implement alert creation
    
    alert_config = AlertConfiguration(
        alert_type=AlertType(alert_data.get("alert_type", "trade_volume")),
        symbol=alert_data.get("symbol"),
        threshold=alert_data.get("threshold"),
        condition=alert_data.get("condition", "above"),
        is_active=alert_data.get("is_active", True),
        notification_channels=alert_data.get("notification_channels", ["email"]),
        description=alert_data.get("description")
    )
    
    data = AlertResponse(
        alert_id=12345,  # Generated ID
        user_id=current_user.id,
        alert_data=alert_config,
        created_at=datetime.utcnow(),
        is_active=True
    )
    
    return create_response(data=data)


@router.put(
    "/alerts/{alert_id}",
    response_model=ResponseEnvelope[AlertResponse],
    responses={
        200: {"description": "Trade alert updated successfully"},
        400: {"description": "Invalid alert configuration"},
        401: {"description": "Not authenticated"},
        404: {"description": "Alert not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_alert(
    alert_id: int = Path(..., description="Alert ID"),
    session: AsyncSession = Depends(get_db_session),
    alert_data: Dict[str, Any] = Body(..., description="Updated alert configuration"),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[AlertResponse]:
    """
    Update an existing trade alert.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Updating alert: alert_id={alert_id}, user_id={current_user.id}, alert_data={alert_data}")
    
    # TODO: Implement alert update with ownership validation
    
    alert_config = AlertConfiguration(
        alert_type=AlertType(alert_data.get("alert_type", "trade_volume")),
        symbol=alert_data.get("symbol"),
        threshold=alert_data.get("threshold"),
        condition=alert_data.get("condition", "above"),
        is_active=alert_data.get("is_active", True),
        notification_channels=alert_data.get("notification_channels", ["email"]),
        description=alert_data.get("description")
    )
    
    data = AlertResponse(
        alert_id=alert_id,
        user_id=current_user.id,
        alert_data=alert_config,
        created_at=datetime.utcnow(),
        is_active=True
    )
    
    return create_response(data=data)


@router.delete(
    "/alerts/{alert_id}",
    response_model=ResponseEnvelope[Dict[str, bool]],
    responses={
        200: {"description": "Trade alert deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Alert not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_alert(
    alert_id: int = Path(..., description="Alert ID"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, bool]]:
    """
    Delete a trade alert.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Deleting alert: alert_id={alert_id}, user_id={current_user.id}")
    
    # TODO: Implement alert deletion with ownership validation
    data = {
        "deleted": True,
        "alert_id": alert_id
    }
    
    return create_response(data=data)


@router.get(
    "/alerts/history",
    response_model=ResponseEnvelope[PaginatedResponse[AlertHistoryItem]],
    responses={
        200: {"description": "Alert history retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_alert_history(
    session: AsyncSession = Depends(get_db_session),
    alert_id: Optional[int] = Query(None, description="Specific alert ID"),
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[AlertHistoryItem]]:
    """
    Get history of triggered alerts for the user.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting alert history: user_id={current_user.id}, alert_id={alert_id}, "
               f"days={days}, skip={skip}, limit={limit}")
    
    # TODO: Implement alert history retrieval
    
    # Create sample history item for demonstration
    history_item = AlertHistoryItem(
        alert_id=alert_id or 12345,
        triggered_at=datetime.utcnow(),
        alert_type=AlertType.TRADE_VOLUME,
        symbol="AAPL",
        threshold=1000.0,
        actual_value=1500.0,
        notification_sent=True,
        delivery_status=DeliveryStatus.DELIVERED
    )
    
    history_items = [history_item] if alert_id else []
    
    # Create pagination meta
    pagination_meta = PaginationMeta(
        page=1,
        per_page=limit,
        total=len(history_items),
        pages=1,
        has_next=False,
        has_prev=False
    )
    
    paginated_data = PaginatedResponse(
        items=history_items,
        meta=pagination_meta
    )
    
    return create_response(data=paginated_data)


@router.get(
    "/newsletter/subscriptions",
    response_model=ResponseEnvelope[NewsletterOptionsResponse],
    responses={
        200: {"description": "Newsletter subscriptions retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_newsletter_subscriptions(
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ResponseEnvelope[NewsletterOptionsResponse]:
    """
    Get available newsletter subscriptions.
    
    Enhanced options for authenticated users.
    """
    logger.info(f"Getting newsletter subscriptions: user_id={current_user.id if current_user else None}")
    
    enhanced_data = current_user is not None
    
    # TODO: Implement newsletter subscription options
    data = NewsletterOptionsResponse(
        newsletters=[],
        user_subscriptions=[] if enhanced_data else None,
        frequencies=["daily", "weekly", "monthly"],
        categories=["trades", "performance", "alerts", "market_summary"],
        enhanced_data=enhanced_data
    )
    
    return create_response(data=data)


@router.post(
    "/newsletter/subscribe",
    response_model=ResponseEnvelope[NewsletterSubscription],
    responses={
        200: {"description": "Newsletter subscription created successfully"},
        400: {"description": "Invalid subscription data"},
        500: {"description": "Internal server error"}
    }
)
async def subscribe_to_newsletter(
    session: AsyncSession = Depends(get_db_session),
    email: str = Body(..., description="Email address"),
    newsletter_type: str = Body("daily", description="Newsletter type"),
    preferences: Optional[Dict[str, Any]] = Body(None, description="Subscription preferences"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ResponseEnvelope[NewsletterSubscription]:
    """
    Subscribe to newsletter (public endpoint, enhanced for authenticated users).
    
    Public endpoint - no authentication required for basic subscription.
    """
    logger.info(f"Newsletter subscription: email={email}, newsletter_type={newsletter_type}, "
               f"user_id={current_user.id if current_user else None}")
    
    # TODO: Implement newsletter subscription
    data = NewsletterSubscription(
        email=email,
        newsletter_type=newsletter_type,
        preferences=preferences or {},
        subscription_id="sub_12345",  # Generated ID
        subscribed_at=datetime.utcnow(),
        confirmation_required=not bool(current_user),  # No confirmation needed for authenticated users
        is_active=True
    )
    
    return create_response(data=data)


@router.post(
    "/newsletter/unsubscribe",
    response_model=ResponseEnvelope[NewsletterUnsubscribeResponse],
    responses={
        200: {"description": "Successfully unsubscribed from newsletter"},
        400: {"description": "Invalid unsubscribe data"},
        500: {"description": "Internal server error"}
    }
)
async def unsubscribe_from_newsletter(
    session: AsyncSession = Depends(get_db_session),
    email: Optional[str] = Body(None, description="Email address (for non-authenticated users)"),
    token: Optional[str] = Body(None, description="Unsubscribe token"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ResponseEnvelope[NewsletterUnsubscribeResponse]:
    """
    Unsubscribe from newsletter.
    
    Can be used by authenticated users or via unsubscribe token.
    """
    logger.info(f"Newsletter unsubscription: email={email}, token={token}, "
               f"user_id={current_user.id if current_user else None}")
    
    # TODO: Implement newsletter unsubscription
    data = NewsletterUnsubscribeResponse(
        email=email or (current_user.email if current_user else None),
        unsubscribed_at=datetime.utcnow(),
        method="authenticated" if current_user else "token"
    )
    
    return create_response(data=data)


@router.get(
    "/templates",
    response_model=ResponseEnvelope[PaginatedResponse[NotificationTemplate]],
    responses={
        200: {"description": "Notification templates retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)
async def get_notification_templates(
    session: AsyncSession = Depends(get_db_session),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    current_user: User = Depends(require_admin()),
) -> ResponseEnvelope[PaginatedResponse[NotificationTemplate]]:
    """
    Get notification templates for administration.
    
    **Admin Only**: Requires enterprise subscription (admin privileges).
    """
    logger.info(f"Getting notification templates: template_type={template_type}, user_id={current_user.id}")
    
    # TODO: Implement template retrieval
    
    # Create sample template for demonstration
    sample_template = NotificationTemplate(
        template_id=1,
        template_type=NotificationType.TRADE_ALERT,
        name="Trade Alert Template",
        subject="New Congressional Trade Alert",
        body_html="<h1>Trade Alert</h1><p>New trade detected...</p>",
        body_text="Trade Alert\n\nNew trade detected...",
        variables=["member_name", "ticker", "amount"],
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    templates = [sample_template] if template_type == "trade_alert" else []
    
    # Create pagination meta
    pagination_meta = PaginationMeta(
        page=1,
        per_page=50,
        total=len(templates),
        pages=1,
        has_next=False,
        has_prev=False
    )
    
    paginated_data = PaginatedResponse(
        items=templates,
        meta=pagination_meta
    )
    
    return create_response(data=paginated_data)


@router.get(
    "/delivery/status",
    response_model=ResponseEnvelope[DeliveryStatusResponse],
    responses={
        200: {"description": "Delivery status retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)
async def get_delivery_status(
    session: AsyncSession = Depends(get_db_session),
    notification_id: Optional[int] = Query(None, description="Specific notification ID"),
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    status: Optional[str] = Query(None, description="Filter by delivery status"),
    current_user: User = Depends(require_admin()),
) -> ResponseEnvelope[DeliveryStatusResponse]:
    """
    Get notification delivery status and metrics.
    
    **Admin Only**: Requires enterprise subscription (admin privileges).
    """
    logger.info(f"Getting delivery status: notification_id={notification_id}, "
               f"days={days}, status={status}, user_id={current_user.id}")
    
    # TODO: Implement delivery status tracking
    data = {
        "delivery_stats": {
            "total_sent": 0,
            "delivered": 0,
            "failed": 0,
            "pending": 0,
            "delivery_rate": 0.0
        },
        "recent_deliveries": [],
        "filters": {
            "notification_id": notification_id,
            "days": days,
            "status": status
        },
        "statuses": ["pending", "delivered", "failed", "bounced", "opened"],
    }
    
    return create_response(data=data)


@router.post(
    "/test/send",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Test notification sent successfully"},
        400: {"description": "Invalid test notification data"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)
async def send_test_notification(
    session: AsyncSession = Depends(get_db_session),
    notification_type: str = Body(..., description="Type of test notification"),
    recipient_email: str = Body(..., description="Test recipient email"),
    test_data: Optional[Dict[str, Any]] = Body(None, description="Test data"),
    current_user: User = Depends(require_admin()),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Send a test notification for development/testing.
    
    **Admin Only**: Requires enterprise subscription (admin privileges).
    """
    logger.info(f"Sending test notification: notification_type={notification_type}, "
               f"recipient_email={recipient_email}, user_id={current_user.id}")
    
    # TODO: Implement test notification sending
    data = {
        "notification_type": notification_type,
        "recipient_email": recipient_email,
        "test_data": test_data or {},
        "sent_at": datetime.utcnow().isoformat(),
        "test_id": "test_12345",  # Generated ID
        "initiated_by": current_user.id,
    }
    
    return create_response(data=data)


@router.get(
    "/analytics",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Notification analytics retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient subscription"},
        500: {"description": "Internal server error"}
    }
)
async def get_notification_analytics(
    session: AsyncSession = Depends(get_db_session),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    current_user: User = Depends(require_subscription(['PREMIUM', 'ENTERPRISE'])),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get notification analytics and engagement metrics.
    
    **Premium Feature**: Requires Premium or Enterprise subscription.
    """
    logger.info(f"Getting notification analytics: date_from={date_from}, date_to={date_to}, "
               f"notification_type={notification_type}, user_id={current_user.id}")
    
    # TODO: Implement notification analytics
    data = {
        "analytics": {
            "total_notifications": 0,
            "open_rate": 0.0,
            "click_rate": 0.0,
            "unsubscribe_rate": 0.0,
            "engagement_score": 0.0
        },
        "trends": [],
        "top_performing": [],
        "date_range": {
            "from": date_from,
            "to": date_to
        },
        "subscription_tier": current_user.subscription_tier,
    }
    
    return create_response(data=data)


# ============================================================================
# WEB PUSH SUBSCRIPTIONS (device registration)
# ============================================================================

@router.get("/push/vapid-key", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_vapid_public_key(
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Public VAPID key the browser needs to subscribe (null if push isn't configured)."""
    from core.config import settings as _settings
    return create_response(data={"public_key": _settings.VAPID_PUBLIC_KEY})


@router.post("/push/subscribe", response_model=ResponseEnvelope[Dict[str, Any]])
async def register_push(
    body: Dict[str, Any] = Body(..., description="Push subscription: endpoint, keys.p256dh, keys.auth"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Register a browser Web Push subscription for the current user."""
    from domains.notifications.channels import register_push_subscription

    endpoint = body.get("endpoint")
    keys = body.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        raise HTTPException(status_code=400, detail="endpoint and keys.p256dh/keys.auth are required")

    await register_push_subscription(
        session, current_user.id, endpoint, keys["p256dh"], keys["auth"], body.get("user_agent")
    )
    return create_response(data={"registered": True})


@router.post("/push/unsubscribe", response_model=ResponseEnvelope[Dict[str, Any]])
async def unregister_push(
    body: Dict[str, Any] = Body(..., description="{ endpoint }"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Deactivate a Web Push subscription for the current user."""
    from domains.notifications.channels import unregister_push_subscription

    endpoint = body.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="endpoint is required")
    ok = await unregister_push_subscription(session, current_user.id, endpoint)
    return create_response(data={"unregistered": ok})


# ============================================================================
# IN-APP NOTIFICATION INBOX (the "bell")
# ============================================================================

@router.get("/inbox", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_inbox(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """List the user's in-app notifications with the unread count."""
    from domains.notifications.inapp_service import InAppNotificationService
    data = await InAppNotificationService(session).list(
        current_user.id, unread_only=unread_only, skip=skip, limit=limit
    )
    return create_response(data=data)


@router.get("/inbox/unread-count", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_inbox_unread_count(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Unread in-app notification count (for the bell badge)."""
    from domains.notifications.inapp_service import InAppNotificationService
    unread = await InAppNotificationService(session).unread_count(current_user.id)
    return create_response(data={"unread": unread})


@router.post("/inbox/read-all", response_model=ResponseEnvelope[Dict[str, Any]])
async def mark_inbox_all_read(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Mark all of the user's in-app notifications as read."""
    from domains.notifications.inapp_service import InAppNotificationService
    count = await InAppNotificationService(session).mark_all_read(current_user.id)
    return create_response(data={"marked_read": count})


@router.post("/inbox/{notification_id}/read", response_model=ResponseEnvelope[Dict[str, Any]])
async def mark_inbox_read(
    notification_id: str = Path(..., description="Notification UUID"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Mark a single in-app notification as read (owner only)."""
    from domains.notifications.inapp_service import InAppNotificationService
    ok = await InAppNotificationService(session).mark_read(current_user.id, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return create_response(data={"marked_read": True, "id": notification_id})


@router.get("/quota", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_usage_quota(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Per-resource usage vs tier limit ({used, limit}; limit -1 = unlimited)."""
    from core.quotas import usage_summary
    data = await usage_summary(session, current_user)
    data["tier"] = getattr(current_user.subscription_tier, "value", str(current_user.subscription_tier))
    return create_response(data=data)


# ============================================================================
# TRADE ALERT ENDPOINTS
# ============================================================================

@router.post(
    "/alerts/member/{member_id}",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Member alert created successfully"},
        400: {"description": "Invalid member ID or alert configuration"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def create_member_alert(
    member_id: str = Path(..., description="Congress member UUID"),
    alert_data: Dict[str, Any] = Body(..., description="Alert configuration"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Subscribe to alerts for a specific congress member's trades.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Creating member alert: member_id={member_id}, user_id={current_user.id}")
    
    try:
        from core.quotas import enforce_quota
        await enforce_quota(session, current_user, "alert_rules")
        notification_service = NotificationService(session)
        data = await notification_service.create_member_alert(current_user.id, member_id, alert_data)
        return create_response(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating member alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create member alert")


@router.post(
    "/alerts/amount",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Amount alert created successfully"},
        400: {"description": "Invalid threshold or alert configuration"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def create_amount_alert(
    alert_data: Dict[str, Any] = Body(..., description="Amount alert configuration"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Create an alert for trades above a certain amount threshold.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Creating amount alert: threshold={alert_data.get('threshold')}, user_id={current_user.id}")
    
    try:
        threshold = alert_data.get("threshold")
        from core.quotas import enforce_quota
        await enforce_quota(session, current_user, "alert_rules")
        notification_service = NotificationService(session)
        data = await notification_service.create_amount_alert(current_user.id, threshold, alert_data)
        return create_response(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating amount alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create amount alert")


@router.post(
    "/alerts/ticker/{ticker}",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Ticker alert created successfully"},
        400: {"description": "Invalid ticker or alert configuration"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def create_ticker_alert(
    ticker: str = Path(..., description="Stock ticker symbol"),
    alert_data: Dict[str, Any] = Body(..., description="Ticker alert configuration"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Subscribe to alerts for trades involving a specific ticker symbol.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Creating ticker alert: ticker={ticker}, user_id={current_user.id}")
    
    try:
        from core.quotas import enforce_quota
        await enforce_quota(session, current_user, "alert_rules")
        notification_service = NotificationService(session)
        data = await notification_service.create_ticker_alert(current_user.id, ticker, alert_data)
        return create_response(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticker alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create ticker alert")


@router.get(
    "/alerts/rules",
    response_model=ResponseEnvelope[PaginatedResponse[Dict[str, Any]]],
    responses={
        200: {"description": "Alert rules retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_user_alert_rules(
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[Dict[str, Any]]]:
    """
    Get user's configured trade alert rules.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting alert rules: user_id={current_user.id}, alert_type={alert_type}, "
               f"is_active={is_active}, skip={skip}, limit={limit}")
    
    try:
        notification_service = NotificationService(session)
        rule_data, total_count = await notification_service.get_user_alert_rules(
            current_user.id, alert_type, is_active, skip, limit
        )
        
        # Create pagination meta
        pagination_meta = PaginationMeta(
            page=(skip // limit) + 1,
            per_page=limit,
            total=total_count,
            pages=(total_count + limit - 1) // limit,
            has_next=skip + limit < total_count,
            has_prev=skip > 0
        )
        
        paginated_data = PaginatedResponse(
            items=rule_data,
            meta=pagination_meta
        )
        
        return create_response(data=paginated_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving alert rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert rules")


@router.get(
    "/alerts/stats",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Alert stats retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_alert_stats(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Dashboard stats for the user's alerts: active alerts, notifications sent
    today, total notifications triggered, and delivery rate.

    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting alert stats: user_id={current_user.id}")
    try:
        notification_service = NotificationService(session)
        data = await notification_service.get_alert_stats(current_user.id)
        return create_response(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving alert stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert stats")


@router.get(
    "/alerts/notifications",
    response_model=ResponseEnvelope[List[Dict[str, Any]]],
    responses={
        200: {"description": "Alert notifications retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_alert_notifications(
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
    status: Optional[str] = Query(None, description="Filter: sent, failed, pending, or all"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[List[Dict[str, Any]]]:
    """
    Delivery history for the user's alerts, with the triggering trade's details.

    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting alert notifications: user_id={current_user.id}, days={days}, "
               f"status={status}, skip={skip}, limit={limit}")
    try:
        notification_service = NotificationService(session)
        data = await notification_service.get_alert_notifications(
            current_user.id, days, status, skip, limit
        )
        return create_response(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving alert notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert notifications")


@router.put(
    "/alerts/rules/{rule_id}",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Alert rule updated successfully"},
        400: {"description": "Invalid rule configuration"},
        401: {"description": "Not authenticated"},
        404: {"description": "Alert rule not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_alert_rule(
    rule_id: int = Path(..., description="Alert rule ID"),
    update_data: Dict[str, Any] = Body(..., description="Updated rule configuration"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Update an existing trade alert rule.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Updating alert rule: rule_id={rule_id}, user_id={current_user.id}")
    
    try:
        notification_service = NotificationService(session)
        data = await notification_service.update_alert_rule(rule_id, current_user.id, update_data)
        return create_response(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert rule")


@router.delete(
    "/alerts/rules/{rule_id}",
    response_model=ResponseEnvelope[Dict[str, bool]],
    responses={
        200: {"description": "Alert rule deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Alert rule not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_alert_rule(
    rule_id: int = Path(..., description="Alert rule ID"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, bool]]:
    """
    Delete a trade alert rule.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Deleting alert rule: rule_id={rule_id}, user_id={current_user.id}")
    
    try:
        notification_service = NotificationService(session)
        data = await notification_service.delete_alert_rule(rule_id, current_user.id)
        return create_response(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert rule") 