"""
Notifications domain package for CapitolScope.

This domain handles email notifications, trade alerts, subscription management,
and user communication preferences.
"""

from .models import (
    NotificationTemplate,
    EmailNotification,
    TradeAlert,
    AlertRule,
    NotificationSubscription,
    NotificationDelivery
)

from .schemas import (
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    EmailNotificationCreate,
    EmailNotificationResponse,
    TradeAlertCreate,
    TradeAlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    NotificationPreferences
)

from .services import NotificationService
from .crud import NotificationCRUD
from .interfaces import NotificationRepositoryProtocol, EmailProviderProtocol

__all__ = [
    # Models
    "NotificationTemplate",
    "EmailNotification",
    "TradeAlert",
    "AlertRule",
    "NotificationSubscription",
    "NotificationDelivery",
    
    # Schemas
    "NotificationTemplateCreate",
    "NotificationTemplateResponse",
    "EmailNotificationCreate",
    "EmailNotificationResponse",
    "TradeAlertCreate",
    "TradeAlertResponse",
    "AlertRuleCreate",
    "AlertRuleResponse",
    "SubscriptionCreate",
    "SubscriptionResponse",
    "NotificationPreferences",
    
    # Services & CRUD
    "NotificationService",
    "NotificationCRUD",
    "NotificationRepositoryProtocol",
    "EmailProviderProtocol",
] 