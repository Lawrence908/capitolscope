"""
Users domain interfaces.

This module defines abstract interfaces for user domain operations,
repositories, and services including authentication and subscription management.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
import uuid

from domains.base.interfaces import (
    BaseRepositoryInterface, BaseServiceInterface, BaseAnalyticsInterface
)
from domains.users.schemas import (
    UserCreate, UserUpdate, UserDetail, UserSummary, UserLogin, UserOAuthLogin,
    PasswordChange, PasswordReset, PasswordResetConfirm, TokenResponse,
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceDetail,
    UserWatchlistCreate, UserWatchlistUpdate, UserWatchlistDetail, UserWatchlistSummary,
    UserAlertCreate, UserAlertUpdate, UserAlertDetail, UserAlertSummary,
    UserNotificationCreate, UserNotificationDetail, UserNotificationSummary,
    SubscriptionUpdate, SubscriptionInfo, ApiKeyCreate, ApiKeyDetail, ApiKeySummary,
    UserQuery, NotificationQuery, WatchlistItemAction
)
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class UserRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user repository operations."""
    
    @abstractmethod
    async def create(self, user_data: UserCreate) -> UserDetail:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[UserDetail]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserDetail]:
        """Get user by email address."""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[UserDetail]:
        """Get user by username."""
        pass
    
    @abstractmethod
    async def get_by_provider_id(self, provider: str, provider_id: str) -> Optional[UserDetail]:
        """Get user by OAuth provider ID."""
        pass
    
    @abstractmethod
    async def update(self, user_id: int, update_data: UserUpdate) -> Optional[UserDetail]:
        """Update user profile."""
        pass
    
    @abstractmethod
    async def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password."""
        pass
    
    @abstractmethod
    async def update_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> UserDetail:
        """Update user subscription information."""
        pass
    
    @abstractmethod
    async def verify_email(self, user_id: int) -> UserDetail:
        """Mark user email as verified."""
        pass
    
    @abstractmethod
    async def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp."""
        pass
    
    @abstractmethod
    async def update_last_active(self, user_id: int) -> bool:
        """Update last active timestamp."""
        pass
    
    @abstractmethod
    async def list_users(self, query: UserQuery) -> Tuple[List[UserSummary], int]:
        """List users with pagination and filtering."""
        pass
    
    @abstractmethod
    async def search_users(self, search_term: str, limit: int = 10) -> List[UserSummary]:
        """Search users by name or email."""
        pass
    
    @abstractmethod
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user usage statistics."""
        pass
    
    @abstractmethod
    async def soft_delete(self, user_id: int) -> bool:
        """Soft delete user account."""
        pass


class UserPreferenceRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user preference operations."""
    
    @abstractmethod
    async def create(self, user_id: int, preferences: UserPreferenceCreate) -> UserPreferenceDetail:
        """Create user preferences."""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Optional[UserPreferenceDetail]:
        """Get user preferences by user ID."""
        pass
    
    @abstractmethod
    async def update(self, user_id: int, update_data: UserPreferenceUpdate) -> UserPreferenceDetail:
        """Update user preferences."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete user preferences."""
        pass


class UserWatchlistRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user watchlist operations."""
    
    @abstractmethod
    async def create(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistDetail:
        """Create a new watchlist."""
        pass
    
    @abstractmethod
    async def get_by_id(self, watchlist_id: int) -> Optional[UserWatchlistDetail]:
        """Get watchlist by ID."""
        pass
    
    @abstractmethod
    async def get_user_watchlists(self, user_id: int) -> List[UserWatchlistSummary]:
        """Get all watchlists for a user."""
        pass
    
    @abstractmethod
    async def get_default_watchlist(self, user_id: int) -> Optional[UserWatchlistDetail]:
        """Get user's default watchlist."""
        pass
    
    @abstractmethod
    async def update(self, watchlist_id: int, update_data: UserWatchlistUpdate) -> UserWatchlistDetail:
        """Update watchlist."""
        pass
    
    @abstractmethod
    async def add_item(self, watchlist_id: int, item_type: str, item_id: int) -> bool:
        """Add item to watchlist."""
        pass
    
    @abstractmethod
    async def remove_item(self, watchlist_id: int, item_type: str, item_id: int) -> bool:
        """Remove item from watchlist."""
        pass
    
    @abstractmethod
    async def delete(self, watchlist_id: int) -> bool:
        """Delete watchlist."""
        pass
    
    @abstractmethod
    async def get_public_watchlists(self, limit: int = 50) -> List[UserWatchlistSummary]:
        """Get public watchlists."""
        pass


class UserAlertRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user alert operations."""
    
    @abstractmethod
    async def create(self, user_id: int, alert_data: UserAlertCreate) -> UserAlertDetail:
        """Create a new alert."""
        pass
    
    @abstractmethod
    async def get_by_id(self, alert_id: int) -> Optional[UserAlertDetail]:
        """Get alert by ID."""
        pass
    
    @abstractmethod
    async def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[UserAlertSummary]:
        """Get all alerts for a user."""
        pass
    
    @abstractmethod
    async def update(self, alert_id: int, update_data: UserAlertUpdate) -> UserAlertDetail:
        """Update alert."""
        pass
    
    @abstractmethod
    async def activate(self, alert_id: int) -> bool:
        """Activate alert."""
        pass
    
    @abstractmethod
    async def deactivate(self, alert_id: int) -> bool:
        """Deactivate alert."""
        pass
    
    @abstractmethod
    async def delete(self, alert_id: int) -> bool:
        """Delete alert."""
        pass
    
    @abstractmethod
    async def trigger_alert(self, alert_id: int) -> bool:
        """Record alert trigger."""
        pass
    
    @abstractmethod
    async def get_alerts_to_check(self) -> List[UserAlertDetail]:
        """Get all active alerts that need to be checked."""
        pass


class UserNotificationRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user notification operations."""
    
    @abstractmethod
    async def create(self, user_id: int, notification_data: UserNotificationCreate) -> UserNotificationDetail:
        """Create a new notification."""
        pass
    
    @abstractmethod
    async def get_by_id(self, notification_id: int) -> Optional[UserNotificationDetail]:
        """Get notification by ID."""
        pass
    
    @abstractmethod
    async def get_user_notifications(self, user_id: int, query: NotificationQuery) -> Tuple[List[UserNotificationSummary], int]:
        """Get notifications for a user with pagination."""
        pass
    
    @abstractmethod
    async def mark_as_read(self, notification_id: int) -> bool:
        """Mark notification as read."""
        pass
    
    @abstractmethod
    async def mark_multiple_as_read(self, notification_ids: List[int]) -> int:
        """Mark multiple notifications as read."""
        pass
    
    @abstractmethod
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        pass
    
    @abstractmethod
    async def delete(self, notification_id: int) -> bool:
        """Delete notification."""
        pass
    
    @abstractmethod
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired notifications."""
        pass


class UserSessionRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user session operations."""
    
    @abstractmethod
    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> str:
        """Create a new user session."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        pass
    
    @abstractmethod
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity."""
        pass
    
    @abstractmethod
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        pass
    
    @abstractmethod
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session."""
        pass
    
    @abstractmethod
    async def terminate_user_sessions(self, user_id: int, except_session_id: Optional[str] = None) -> int:
        """Terminate all sessions for a user."""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        pass


class UserApiKeyRepositoryInterface(BaseRepositoryInterface, ABC):
    """Abstract interface for user API key operations."""
    
    @abstractmethod
    async def create(self, user_id: int, key_data: ApiKeyCreate) -> ApiKeyDetail:
        """Create a new API key."""
        pass
    
    @abstractmethod
    async def get_by_key_id(self, key_id: uuid.UUID) -> Optional[ApiKeySummary]:
        """Get API key by key ID."""
        pass
    
    @abstractmethod
    async def get_user_keys(self, user_id: int) -> List[ApiKeySummary]:
        """Get all API keys for a user."""
        pass
    
    @abstractmethod
    async def verify_key(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return key info."""
        pass
    
    @abstractmethod
    async def update(self, key_id: uuid.UUID, update_data: Dict[str, Any]) -> ApiKeySummary:
        """Update API key."""
        pass
    
    @abstractmethod
    async def record_usage(self, key_id: uuid.UUID) -> bool:
        """Record API key usage."""
        pass
    
    @abstractmethod
    async def revoke(self, key_id: uuid.UUID) -> bool:
        """Revoke API key."""
        pass
    
    @abstractmethod
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys."""
        pass


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class AuthenticationServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for authentication business logic."""
    
    @abstractmethod
    async def register_user(self, user_data: UserCreate) -> UserDetail:
        """Register a new user."""
        pass
    
    @abstractmethod
    async def authenticate_user(self, login_data: UserLogin) -> Tuple[UserDetail, TokenResponse]:
        """Authenticate user with email/password."""
        pass
    
    @abstractmethod
    async def authenticate_oauth(self, oauth_data: UserOAuthLogin) -> Tuple[UserDetail, TokenResponse]:
        """Authenticate user with OAuth provider."""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token."""
        pass
    
    @abstractmethod
    async def logout_user(self, user_id: int, session_id: str) -> bool:
        """Logout user and terminate session."""
        pass
    
    @abstractmethod
    async def change_password(self, user_id: int, password_change: PasswordChange) -> bool:
        """Change user password."""
        pass
    
    @abstractmethod
    async def reset_password_request(self, email: str) -> bool:
        """Send password reset email."""
        pass
    
    @abstractmethod
    async def reset_password_confirm(self, reset_data: PasswordResetConfirm) -> bool:
        """Confirm password reset."""
        pass
    
    @abstractmethod
    async def verify_email(self, verification_token: str) -> UserDetail:
        """Verify user email address."""
        pass
    
    @abstractmethod
    async def resend_verification(self, email: str) -> bool:
        """Resend email verification."""
        pass


class UserManagementServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for user management business logic."""
    
    @abstractmethod
    async def get_user_profile(self, user_id: int) -> UserDetail:
        """Get complete user profile."""
        pass
    
    @abstractmethod
    async def update_user_profile(self, user_id: int, update_data: UserUpdate) -> UserDetail:
        """Update user profile."""
        pass
    
    @abstractmethod
    async def delete_user_account(self, user_id: int) -> bool:
        """Delete user account (soft delete)."""
        pass
    
    @abstractmethod
    async def get_user_preferences(self, user_id: int) -> UserPreferenceDetail:
        """Get user preferences."""
        pass
    
    @abstractmethod
    async def update_user_preferences(self, user_id: int, preferences: UserPreferenceUpdate) -> UserPreferenceDetail:
        """Update user preferences."""
        pass
    
    @abstractmethod
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user activity statistics."""
        pass


class WatchlistServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for watchlist management business logic."""
    
    @abstractmethod
    async def create_watchlist(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistDetail:
        """Create a new watchlist."""
        pass
    
    @abstractmethod
    async def get_user_watchlists(self, user_id: int) -> List[UserWatchlistSummary]:
        """Get all watchlists for a user."""
        pass
    
    @abstractmethod
    async def get_watchlist(self, watchlist_id: int, user_id: int) -> UserWatchlistDetail:
        """Get specific watchlist."""
        pass
    
    @abstractmethod
    async def update_watchlist(self, watchlist_id: int, user_id: int, update_data: UserWatchlistUpdate) -> UserWatchlistDetail:
        """Update watchlist."""
        pass
    
    @abstractmethod
    async def manage_watchlist_items(self, watchlist_id: int, user_id: int, action: WatchlistItemAction) -> bool:
        """Add or remove items from watchlist."""
        pass
    
    @abstractmethod
    async def delete_watchlist(self, watchlist_id: int, user_id: int) -> bool:
        """Delete watchlist."""
        pass
    
    @abstractmethod
    async def get_watchlist_performance(self, watchlist_id: int, user_id: int) -> Dict[str, Any]:
        """Get performance metrics for watchlist items."""
        pass


class AlertServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for alert management business logic."""
    
    @abstractmethod
    async def create_alert(self, user_id: int, alert_data: UserAlertCreate) -> UserAlertDetail:
        """Create a new alert."""
        pass
    
    @abstractmethod
    async def get_user_alerts(self, user_id: int) -> List[UserAlertSummary]:
        """Get all alerts for a user."""
        pass
    
    @abstractmethod
    async def get_alert(self, alert_id: int, user_id: int) -> UserAlertDetail:
        """Get specific alert."""
        pass
    
    @abstractmethod
    async def update_alert(self, alert_id: int, user_id: int, update_data: UserAlertUpdate) -> UserAlertDetail:
        """Update alert."""
        pass
    
    @abstractmethod
    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete alert."""
        pass
    
    @abstractmethod
    async def check_alerts(self) -> int:
        """Check all active alerts and trigger notifications."""
        pass
    
    @abstractmethod
    async def validate_alert_conditions(self, alert_data: UserAlertCreate) -> bool:
        """Validate alert conditions."""
        pass


class NotificationServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for notification management business logic."""
    
    @abstractmethod
    async def send_notification(self, user_id: int, notification_data: UserNotificationCreate) -> UserNotificationDetail:
        """Send notification to user."""
        pass
    
    @abstractmethod
    async def get_user_notifications(self, user_id: int, query: NotificationQuery) -> Tuple[List[UserNotificationSummary], int]:
        """Get notifications for a user."""
        pass
    
    @abstractmethod
    async def mark_notifications_read(self, user_id: int, notification_ids: List[int]) -> int:
        """Mark notifications as read."""
        pass
    
    @abstractmethod
    async def get_unread_count(self, user_id: int) -> int:
        """Get unread notification count."""
        pass
    
    @abstractmethod
    async def send_bulk_notification(self, user_ids: List[int], notification_data: UserNotificationCreate) -> int:
        """Send notification to multiple users."""
        pass
    
    @abstractmethod
    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """Clean up old notifications."""
        pass


class SubscriptionServiceInterface(BaseServiceInterface, ABC):
    """Abstract interface for subscription management business logic."""
    
    @abstractmethod
    async def get_subscription_info(self, user_id: int) -> SubscriptionInfo:
        """Get user subscription information."""
        pass
    
    @abstractmethod
    async def upgrade_subscription(self, user_id: int, subscription_data: SubscriptionUpdate) -> SubscriptionInfo:
        """Upgrade user subscription."""
        pass
    
    @abstractmethod
    async def downgrade_subscription(self, user_id: int, subscription_data: SubscriptionUpdate) -> SubscriptionInfo:
        """Downgrade user subscription."""
        pass
    
    @abstractmethod
    async def cancel_subscription(self, user_id: int, cancellation_data: Dict[str, Any]) -> bool:
        """Cancel user subscription."""
        pass
    
    @abstractmethod
    async def reactivate_subscription(self, user_id: int) -> SubscriptionInfo:
        """Reactivate cancelled subscription."""
        pass
    
    @abstractmethod
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Process subscription webhook from payment provider."""
        pass
    
    @abstractmethod
    async def check_subscription_limits(self, user_id: int, feature: str) -> bool:
        """Check if user can access feature based on subscription."""
        pass


# ============================================================================
# ANALYTICS INTERFACES
# ============================================================================

class UserAnalyticsInterface(BaseAnalyticsInterface, ABC):
    """Abstract interface for user analytics."""
    
    @abstractmethod
    async def get_user_engagement_metrics(self, user_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Get user engagement metrics."""
        pass
    
    @abstractmethod
    async def get_feature_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get feature usage statistics."""
        pass
    
    @abstractmethod
    async def get_platform_analytics(self) -> Dict[str, Any]:
        """Get platform-wide user analytics."""
        pass
    
    @abstractmethod
    async def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get subscription analytics."""
        pass
    
    @abstractmethod
    async def get_user_cohort_analysis(self, period: str = "monthly") -> Dict[str, Any]:
        """Get user cohort analysis."""
        pass
    
    @abstractmethod
    async def track_user_action(self, user_id: int, action: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track user action for analytics."""
        pass


# ============================================================================
# EXTERNAL SERVICE INTERFACES
# ============================================================================

class EmailServiceInterface(ABC):
    """Abstract interface for email service."""
    
    @abstractmethod
    async def send_verification_email(self, email: str, verification_link: str) -> bool:
        """Send email verification."""
        pass
    
    @abstractmethod
    async def send_password_reset_email(self, email: str, reset_link: str) -> bool:
        """Send password reset email."""
        pass
    
    @abstractmethod
    async def send_notification_email(self, email: str, subject: str, content: str) -> bool:
        """Send notification email."""
        pass
    
    @abstractmethod
    async def send_welcome_email(self, email: str, user_name: str) -> bool:
        """Send welcome email."""
        pass


class SmsServiceInterface(ABC):
    """Abstract interface for SMS service."""
    
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message."""
        pass


class PushNotificationServiceInterface(ABC):
    """Abstract interface for push notification service."""
    
    @abstractmethod
    async def send_push_notification(self, user_id: int, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send push notification."""
        pass


# Log interface creation
logger.info("Users domain interfaces initialized")

# Export all interfaces
__all__ = [
    # Repository interfaces
    "UserRepositoryInterface",
    "UserPreferenceRepositoryInterface",
    "UserWatchlistRepositoryInterface", 
    "UserAlertRepositoryInterface",
    "UserNotificationRepositoryInterface",
    "UserSessionRepositoryInterface",
    "UserApiKeyRepositoryInterface",
    
    # Service interfaces
    "AuthenticationServiceInterface",
    "UserManagementServiceInterface",
    "WatchlistServiceInterface",
    "AlertServiceInterface", 
    "NotificationServiceInterface",
    "SubscriptionServiceInterface",
    
    # Analytics interfaces
    "UserAnalyticsInterface",
    
    # External service interfaces
    "EmailServiceInterface",
    "SmsServiceInterface", 
    "PushNotificationServiceInterface"
] 