"""
Notifications domain package for CapitolScope.

This domain handles email notifications, trade alerts, subscription management,
and user communication preferences.
"""

from .models import (
    NotificationSubscription,
    NotificationAlert,
    NotificationDeliveryLog,
    NotificationTemplate,
    NewsletterSubscription,
    NotificationAnalytics
)

from .schemas import (
    UserSubscriptionResponse,
    SubscriptionUpdateResponse,
    AlertListResponse,
    AlertResponse,
    AlertHistoryResponse,
    NewsletterOptionsResponse,
    NewsletterSubscription,
    NewsletterUnsubscribeResponse,
    TemplateListResponse,
    DeliveryStatusResponse,
    TestNotificationResponse,
    NotificationAnalyticsResponse
)

from .services import NotificationService
from .crud import NotificationCRUD
from .interfaces import NotificationRepositoryProtocol, EmailProviderProtocol

__all__ = [
    # Models
    "NotificationSubscription",
    "NotificationAlert",
    "NotificationDeliveryLog",
    "NotificationTemplate",
    "NewsletterSubscription",
    "NotificationAnalytics",
    
    # Schemas
    "UserSubscriptionResponse",
    "SubscriptionUpdateResponse",
    "AlertListResponse",
    "AlertResponse",
    "AlertHistoryResponse",
    "NewsletterOptionsResponse",
    "NewsletterSubscription",
    "NewsletterUnsubscribeResponse",
    "TemplateListResponse",
    "DeliveryStatusResponse",
    "TestNotificationResponse",
    "NotificationAnalyticsResponse",
    
    # Services & CRUD
    "NotificationService",
    "NotificationCRUD",
    "NotificationRepositoryProtocol",
    "EmailProviderProtocol",
] 