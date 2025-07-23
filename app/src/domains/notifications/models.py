"""
Notification domain models.

This module defines SQLAlchemy models for notification management,
including user subscriptions, alerts, and delivery tracking.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from domains.base.models import CapitolScopeBaseModel, TimestampMixin


# ============================================================================
# NOTIFICATION MODELS
# ============================================================================

class NotificationSubscription(CapitolScopeBaseModel):
    """User notification subscription preferences."""
    __tablename__ = "notification_subscriptions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Subscription preferences
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=False)
    sms_enabled = Column(Boolean, default=False)
    
    # Notification types
    trade_alerts = Column(Boolean, default=True)
    portfolio_updates = Column(Boolean, default=True)
    market_alerts = Column(Boolean, default=False)
    newsletter = Column(Boolean, default=True)
    
    # Frequency settings
    email_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    alert_threshold = Column(Integer, default=10000)  # Minimum trade amount for alerts
    
    # Metadata
    # created_at and updated_at are provided by CapitolScopeBaseModel
    
    # Relationships
    user = relationship("User", back_populates="notification_subscriptions")
    alerts = relationship("NotificationAlert", back_populates="subscription")


class NotificationAlert(CapitolScopeBaseModel):
    """Individual notification alerts."""
    __tablename__ = "notification_alerts"
    
    subscription_id = Column(Integer, ForeignKey("notification_subscriptions.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # trade_alert, portfolio_update, market_alert
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert data
    data = Column(JSON)  # Additional context data
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Delivery status
    email_sent = Column(Boolean, default=False)
    push_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)
    
    # Timestamps
    # created_at is provided by CapitolScopeBaseModel
    sent_at = Column(DateTime)
    read_at = Column(DateTime)
    
    # Relationships
    subscription = relationship("NotificationSubscription", back_populates="alerts")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="alert")


class NotificationDeliveryLog(CapitolScopeBaseModel):
    """Log of notification delivery attempts."""
    __tablename__ = "notification_delivery_logs"
    
    alert_id = Column(Integer, ForeignKey("notification_alerts.id"), nullable=False)
    
    # Delivery details
    delivery_method = Column(String(20), nullable=False)  # email, push, sms
    recipient = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # pending, sent, failed, delivered
    
    # Delivery metadata
    provider_response = Column(Text)  # Response from delivery provider
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    # created_at is provided by CapitolScopeBaseModel
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    # Relationships
    alert = relationship("NotificationAlert", back_populates="delivery_logs")


class NotificationTemplate(CapitolScopeBaseModel):
    """Email and notification templates."""
    __tablename__ = "notification_templates"
    
    # Template details
    name = Column(String(100), nullable=False, unique=True)
    template_type = Column(String(50), nullable=False)  # email, push, sms
    subject = Column(String(255))  # For email templates
    
    # Template content
    html_content = Column(Text)  # HTML version for emails
    text_content = Column(Text)  # Plain text version
    variables = Column(JSON)  # Template variables and defaults
    
    # Template settings
    is_active = Column(Boolean, default=True)
    version = Column(String(20), default="1.0")
    
    # Metadata
    # created_at and updated_at are provided by CapitolScopeBaseModel


class NewsletterSubscription(CapitolScopeBaseModel):
    """Newsletter subscription management."""
    __tablename__ = "newsletter_subscriptions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    email = Column(String(255), nullable=False)
    newsletter_type = Column(String(50), default="general")  # general, trading, market
    frequency = Column(String(20), default="weekly")  # daily, weekly, monthly
    
    # Status
    is_active = Column(Boolean, default=True)
    confirmed_at = Column(DateTime)
    unsubscribed_at = Column(DateTime)
    
    # Metadata
    # created_at and updated_at are provided by CapitolScopeBaseModel
    
    # Relationships
    user = relationship("User", back_populates="newsletter_subscriptions")


class NotificationAnalytics(CapitolScopeBaseModel):
    """Analytics data for notification performance."""
    __tablename__ = "notification_analytics"
    
    # Analytics period
    date = Column(DateTime, nullable=False)
    period_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Delivery metrics
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_clicked = Column(Integer, default=0)
    
    # Performance metrics
    delivery_rate = Column(Integer, default=0)  # Percentage
    open_rate = Column(Integer, default=0)  # Percentage
    click_rate = Column(Integer, default=0)  # Percentage
    
    # Channel breakdown
    email_sent = Column(Integer, default=0)
    push_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    
    # Metadata
    # created_at is provided by CapitolScopeBaseModel


# ============================================================================
# MODEL RELATIONSHIPS
# ============================================================================

# Add relationships to User model (if it exists)
# This would typically be done in the User model file
# User.notification_subscriptions = relationship("NotificationSubscription", back_populates="user")
# User.newsletter_subscriptions = relationship("NewsletterSubscription", back_populates="user")


# ============================================================================
# MODEL EXPORTS
# ============================================================================

__all__ = [
    "NotificationSubscription",
    "NotificationAlert", 
    "NotificationDeliveryLog",
    "NotificationTemplate",
    "NewsletterSubscription",
    "NotificationAnalytics"
] 