"""
Notification schemas for the CapitolScope API.

This module contains Pydantic schemas for notifications, alerts,
subscriptions, and delivery tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import Field, field_validator

from schemas.base import CapitolScopeBaseModel, UUIDMixin, TimestampMixin


# ============================================================================
# ENUMS
# ============================================================================

class NotificationType(str, Enum):
    """Notification types."""
    TRADE_ALERT = "trade_alert"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_ALERT = "market_alert"
    NEWSLETTER = "newsletter"
    WELCOME = "welcome"
    SYSTEM = "system"


class AlertType(str, Enum):
    """Alert types."""
    TRADE_VOLUME = "trade_volume"
    PRICE_CHANGE = "price_change"
    NEW_FILING = "new_filing"
    PORTFOLIO_CHANGE = "portfolio_change"
    MARKET_MOVEMENT = "market_movement"


class DeliveryStatus(str, Enum):
    """Delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"


class SubscriptionFrequency(str, Enum):
    """Subscription frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    IMMEDIATE = "immediate"


# ============================================================================
# SUBSCRIPTION SCHEMAS
# ============================================================================

class SubscriptionPreferences(CapitolScopeBaseModel):
    """User notification preferences."""
    email_frequency: SubscriptionFrequency = Field(SubscriptionFrequency.DAILY, description="Email frequency")
    trade_alerts: bool = Field(True, description="Enable trade alerts")
    portfolio_updates: bool = Field(True, description="Enable portfolio updates")
    market_alerts: bool = Field(False, description="Enable market alerts")
    newsletter: bool = Field(True, description="Enable newsletter")
    push_notifications: bool = Field(False, description="Enable push notifications")
    sms_notifications: bool = Field(False, description="Enable SMS notifications")


class UserSubscriptionResponse(CapitolScopeBaseModel):
    """User subscription response."""
    user_id: int = Field(..., description="User ID")
    subscriptions: List[str] = Field(default_factory=list, description="Active subscription types")
    preferences: SubscriptionPreferences = Field(..., description="User preferences")
    total_subscriptions: int = Field(0, description="Total active subscriptions")
    last_updated: datetime = Field(..., description="Last preferences update")


class SubscriptionUpdateRequest(CapitolScopeBaseModel):
    """Request to update subscription preferences."""
    preferences: SubscriptionPreferences = Field(..., description="Updated preferences")


class SubscriptionUpdateResponse(CapitolScopeBaseModel):
    """Response for subscription update."""
    user_id: int = Field(..., description="User ID")
    updated_preferences: SubscriptionPreferences = Field(..., description="Updated preferences")
    updated_at: datetime = Field(..., description="Update timestamp")


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertConfiguration(CapitolScopeBaseModel):
    """Alert configuration."""
    alert_type: AlertType = Field(..., description="Type of alert")
    symbol: Optional[str] = Field(None, description="Stock symbol for symbol-specific alerts")
    threshold: Optional[float] = Field(None, description="Alert threshold")
    condition: str = Field(..., description="Alert condition (above, below, equals)")
    is_active: bool = Field(True, description="Whether alert is active")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    description: Optional[str] = Field(None, description="Alert description")


class AlertResponse(CapitolScopeBaseModel):
    """Alert response."""
    alert_id: int = Field(..., description="Alert ID")
    user_id: int = Field(..., description="User ID")
    alert_data: AlertConfiguration = Field(..., description="Alert configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    is_active: bool = Field(True, description="Active status")


class AlertHistoryItem(CapitolScopeBaseModel):
    """Alert history item."""
    alert_id: int = Field(..., description="Alert ID")
    triggered_at: datetime = Field(..., description="Trigger timestamp")
    alert_type: AlertType = Field(..., description="Alert type")
    symbol: Optional[str] = Field(None, description="Stock symbol")
    threshold: Optional[float] = Field(None, description="Alert threshold")
    actual_value: Optional[float] = Field(None, description="Actual value that triggered alert")
    notification_sent: bool = Field(True, description="Whether notification was sent")
    delivery_status: Optional[DeliveryStatus] = Field(None, description="Delivery status")


class AlertHistoryResponse(CapitolScopeBaseModel):
    """Alert history response."""
    user_id: int = Field(..., description="User ID")
    alert_history: List[AlertHistoryItem] = Field(default_factory=list, description="Alert history")
    total: int = Field(0, description="Total history items")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class AlertListResponse(CapitolScopeBaseModel):
    """Alert list response."""
    user_id: int = Field(..., description="User ID")
    alerts: List[AlertResponse] = Field(default_factory=list, description="User alerts")
    total: int = Field(0, description="Total alerts")
    alert_types: List[str] = Field(default_factory=list, description="Available alert types")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


# ============================================================================
# NEWSLETTER SCHEMAS
# ============================================================================

class NewsletterSubscription(CapitolScopeBaseModel):
    """Newsletter subscription."""
    email: str = Field(..., description="Email address")
    newsletter_type: str = Field(..., description="Newsletter type")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Subscription preferences")
    subscription_id: str = Field(..., description="Subscription ID")
    subscribed_at: datetime = Field(..., description="Subscription timestamp")
    confirmation_required: bool = Field(False, description="Whether confirmation is required")
    is_active: bool = Field(True, description="Active status")


class NewsletterSubscriptionRequest(CapitolScopeBaseModel):
    """Newsletter subscription request."""
    email: str = Field(..., description="Email address")
    newsletter_type: str = Field("daily", description="Newsletter type")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Subscription preferences")


class NewsletterUnsubscribeRequest(CapitolScopeBaseModel):
    """Newsletter unsubscribe request."""
    email: Optional[str] = Field(None, description="Email address (for non-authenticated users)")
    token: Optional[str] = Field(None, description="Unsubscribe token")


class NewsletterUnsubscribeResponse(CapitolScopeBaseModel):
    """Newsletter unsubscribe response."""
    email: Optional[str] = Field(None, description="Email address")
    unsubscribed_at: datetime = Field(..., description="Unsubscribe timestamp")
    method: str = Field(..., description="Unsubscribe method (authenticated or token)")


class NewsletterOptionsResponse(CapitolScopeBaseModel):
    """Newsletter subscription options."""
    newsletters: List[Dict[str, Any]] = Field(default_factory=list, description="Available newsletters")
    user_subscriptions: Optional[List[str]] = Field(None, description="User's active subscriptions")
    frequencies: List[str] = Field(default_factory=list, description="Available frequencies")
    categories: List[str] = Field(default_factory=list, description="Available categories")
    enhanced_data: bool = Field(False, description="Whether enhanced data is available")


# ============================================================================
# TEMPLATE SCHEMAS
# ============================================================================

class NotificationTemplate(CapitolScopeBaseModel):
    """Notification template."""
    template_id: int = Field(..., description="Template ID")
    template_type: NotificationType = Field(..., description="Template type")
    name: str = Field(..., description="Template name")
    subject: str = Field(..., description="Email subject")
    body_html: str = Field(..., description="HTML body")
    body_text: str = Field(..., description="Text body")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    is_active: bool = Field(True, description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TemplateListResponse(CapitolScopeBaseModel):
    """Template list response."""
    templates: List[NotificationTemplate] = Field(default_factory=list, description="Templates")
    total: int = Field(0, description="Total templates")
    template_types: List[str] = Field(default_factory=list, description="Available template types")
    filter: Dict[str, Any] = Field(default_factory=dict, description="Applied filter")


# ============================================================================
# DELIVERY TRACKING SCHEMAS
# ============================================================================

class DeliveryStats(CapitolScopeBaseModel):
    """Delivery statistics."""
    total_sent: int = Field(0, description="Total notifications sent")
    delivered: int = Field(0, description="Successfully delivered")
    failed: int = Field(0, description="Failed deliveries")
    pending: int = Field(0, description="Pending deliveries")
    delivery_rate: float = Field(0.0, description="Delivery success rate")


class DeliveryStatusResponse(CapitolScopeBaseModel):
    """Delivery status response."""
    delivery_stats: DeliveryStats = Field(..., description="Delivery statistics")
    recent_deliveries: List[Dict[str, Any]] = Field(default_factory=list, description="Recent deliveries")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    statuses: List[str] = Field(default_factory=list, description="Available statuses")


# ============================================================================
# TEST NOTIFICATION SCHEMAS
# ============================================================================

class TestNotificationRequest(CapitolScopeBaseModel):
    """Test notification request."""
    notification_type: str = Field(..., description="Type of test notification")
    recipient_email: str = Field(..., description="Test recipient email")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test data")


class TestNotificationResponse(CapitolScopeBaseModel):
    """Test notification response."""
    notification_type: str = Field(..., description="Notification type")
    recipient_email: str = Field(..., description="Recipient email")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Test data")
    sent_at: datetime = Field(..., description="Send timestamp")
    test_id: str = Field(..., description="Test ID")
    initiated_by: int = Field(..., description="User who initiated test")


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class NotificationAnalytics(CapitolScopeBaseModel):
    """Notification analytics."""
    total_notifications: int = Field(0, description="Total notifications")
    open_rate: float = Field(0.0, description="Email open rate")
    click_rate: float = Field(0.0, description="Click-through rate")
    unsubscribe_rate: float = Field(0.0, description="Unsubscribe rate")
    engagement_score: float = Field(0.0, description="Overall engagement score")


class NotificationAnalyticsResponse(CapitolScopeBaseModel):
    """Notification analytics response."""
    analytics: NotificationAnalytics = Field(..., description="Analytics data")
    trends: List[Dict[str, Any]] = Field(default_factory=list, description="Trend data")
    top_performing: List[Dict[str, Any]] = Field(default_factory=list, description="Top performing notifications")
    date_range: Dict[str, Any] = Field(default_factory=dict, description="Date range")
    subscription_tier: str = Field(..., description="User subscription tier") 