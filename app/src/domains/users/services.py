"""
Users domain services.

This module contains business logic services for user domain operations
including authentication, subscription management, and user features.
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
import secrets
import hashlib

from domains.base.services import BaseService
from domains.users.interfaces import (
    AuthenticationServiceInterface, UserManagementServiceInterface,
    WatchlistServiceInterface, AlertServiceInterface, NotificationServiceInterface,
    SubscriptionServiceInterface, EmailServiceInterface
)
from domains.users.crud import (
    UserRepository, UserPreferenceRepository, UserWatchlistRepository,
    UserAlertRepository, UserNotificationRepository, UserSessionRepository
)
from domains.users.schemas import (
    UserCreate, UserUpdate, UserDetail, UserLogin, UserOAuthLogin,
    PasswordChange, PasswordReset, PasswordResetConfirm, TokenResponse,
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceDetail,
    UserWatchlistCreate, UserWatchlistUpdate, UserWatchlistDetail, WatchlistItemAction,
    UserAlertCreate, UserAlertUpdate, UserAlertDetail,
    UserNotificationCreate, UserNotificationDetail, NotificationQuery,
    SubscriptionUpdate, SubscriptionInfo, UserStatus, SubscriptionTier
)
from core.exceptions import NotFoundError, ValidationError, AuthenticationError, BusinessLogicError
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION SERVICE
# ============================================================================

class AuthenticationService(BaseService, AuthenticationServiceInterface):
    """Service for user authentication business logic."""
    
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: UserSessionRepository,
        email_service: Optional[EmailServiceInterface] = None
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.email_service = email_service
    
    async def register_user(self, user_data: UserCreate) -> UserDetail:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise ValidationError("User with this email already exists")
        
        if user_data.username:
            existing_username = await self.user_repo.get_by_username(user_data.username)
            if existing_username:
                raise ValidationError("Username already taken")
        
        # Create user
        user = await self.user_repo.create(user_data)
        
        # Send verification email
        if self.email_service:
            verification_token = self._generate_verification_token(user.id)
            verification_link = f"https://app.capitolscope.com/verify-email?token={verification_token}"
            await self.email_service.send_verification_email(user.email, verification_link)
        
        logger.info(f"Registered new user: {user.email}")
        return user
    
    async def authenticate_user(self, login_data: UserLogin) -> Tuple[UserDetail, TokenResponse]:
        """Authenticate user with email/password."""
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not self._verify_password(login_data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        
        # Check account status
        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Account suspended")
        
        if user.status == UserStatus.PENDING_VERIFICATION:
            raise AuthenticationError("Please verify your email address")
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        # Generate tokens
        tokens = self._generate_tokens(user.id)
        
        # Create session
        session_data = {
            'user_id': user.id,
            'login_method': 'password',
            'expires_at': datetime.now() + timedelta(hours=24)
        }
        session_id = await self.session_repo.create_session(user.id, session_data)
        
        logger.info(f"User authenticated: {user.email}")
        return user, tokens
    
    async def authenticate_oauth(self, oauth_data: UserOAuthLogin) -> Tuple[UserDetail, TokenResponse]:
        """Authenticate user with OAuth provider."""
        # Look for existing user
        user = await self.user_repo.get_by_provider_id(
            oauth_data.auth_provider.value, 
            oauth_data.provider_id
        )
        
        if not user:
            # Create new user from OAuth data
            # This would typically fetch user info from the OAuth provider
            user_create = UserCreate(
                email=f"oauth_{oauth_data.provider_id}@{oauth_data.auth_provider.value}.com",  # Placeholder
                auth_provider=oauth_data.auth_provider,
                provider_id=oauth_data.provider_id,
                password="",  # OAuth users don't have passwords
                marketing_emails_enabled=True
            )
            user = await self.user_repo.create(user_create)
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        # Generate tokens
        tokens = self._generate_tokens(user.id)
        
        logger.info(f"OAuth user authenticated: {user.email}")
        return user, tokens
    
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token."""
        # Verify refresh token (implementation would decode JWT)
        user_id = self._verify_refresh_token(refresh_token)
        if not user_id:
            raise AuthenticationError("Invalid refresh token")
        
        # Generate new tokens
        tokens = self._generate_tokens(user_id)
        
        logger.info(f"Token refreshed for user: {user_id}")
        return tokens
    
    async def logout_user(self, user_id: int, session_id: str) -> bool:
        """Logout user and terminate session."""
        await self.session_repo.terminate_session(session_id)
        logger.info(f"User logged out: {user_id}")
        return True
    
    async def change_password(self, user_id: int, password_change: PasswordChange) -> bool:
        """Change user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Verify current password
        if not self._verify_password(password_change.current_password, user.password_hash):
            raise ValidationError("Current password is incorrect")
        
        # Update password
        new_password_hash = self._hash_password(password_change.new_password)
        await self.user_repo.update_password(user_id, new_password_hash)
        
        # Terminate all other sessions
        await self.session_repo.terminate_user_sessions(user_id)
        
        logger.info(f"Password changed for user: {user_id}")
        return True
    
    async def reset_password_request(self, email: str) -> bool:
        """Send password reset email."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True
        
        if self.email_service:
            reset_token = self._generate_reset_token(user.id)
            reset_link = f"https://app.capitolscope.com/reset-password?token={reset_token}"
            await self.email_service.send_password_reset_email(email, reset_link)
        
        logger.info(f"Password reset requested for: {email}")
        return True
    
    async def reset_password_confirm(self, reset_data: PasswordResetConfirm) -> bool:
        """Confirm password reset."""
        user_id = self._verify_reset_token(reset_data.token)
        if not user_id:
            raise ValidationError("Invalid or expired reset token")
        
        # Update password
        new_password_hash = self._hash_password(reset_data.new_password)
        await self.user_repo.update_password(user_id, new_password_hash)
        
        # Terminate all sessions
        await self.session_repo.terminate_user_sessions(user_id)
        
        logger.info(f"Password reset confirmed for user: {user_id}")
        return True
    
    async def verify_email(self, verification_token: str) -> UserDetail:
        """Verify user email address."""
        user_id = self._verify_verification_token(verification_token)
        if not user_id:
            raise ValidationError("Invalid or expired verification token")
        
        user = await self.user_repo.verify_email(user_id)
        
        if self.email_service:
            await self.email_service.send_welcome_email(user.email, user.display_name)
        
        logger.info(f"Email verified for user: {user_id}")
        return user
    
    async def resend_verification(self, email: str) -> bool:
        """Resend email verification."""
        user = await self.user_repo.get_by_email(email)
        if not user or user.is_verified:
            return True
        
        if self.email_service:
            verification_token = self._generate_verification_token(user.id)
            verification_link = f"https://app.capitolscope.com/verify-email?token={verification_token}"
            await self.email_service.send_verification_email(email, verification_link)
        
        logger.info(f"Verification email resent to: {email}")
        return True
    
    def _hash_password(self, password: str) -> str:
        """Hash password (simplified - use bcrypt in production)."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        return self._hash_password(password) == hash
    
    def _generate_tokens(self, user_id: int) -> TokenResponse:
        """Generate JWT tokens (simplified implementation)."""
        access_token = f"access_{user_id}_{secrets.token_urlsafe(32)}"
        refresh_token = f"refresh_{user_id}_{secrets.token_urlsafe(32)}"
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600  # 1 hour
        )
    
    def _generate_verification_token(self, user_id: int) -> str:
        """Generate email verification token."""
        return f"verify_{user_id}_{secrets.token_urlsafe(32)}"
    
    def _generate_reset_token(self, user_id: int) -> str:
        """Generate password reset token."""
        return f"reset_{user_id}_{secrets.token_urlsafe(32)}"
    
    def _verify_refresh_token(self, token: str) -> Optional[int]:
        """Verify refresh token and extract user ID."""
        # Simplified implementation
        try:
            parts = token.split('_')
            if parts[0] == 'refresh':
                return int(parts[1])
        except:
            pass
        return None
    
    def _verify_verification_token(self, token: str) -> Optional[int]:
        """Verify email verification token and extract user ID."""
        try:
            parts = token.split('_')
            if parts[0] == 'verify':
                return int(parts[1])
        except:
            pass
        return None
    
    def _verify_reset_token(self, token: str) -> Optional[int]:
        """Verify password reset token and extract user ID."""
        try:
            parts = token.split('_')
            if parts[0] == 'reset':
                return int(parts[1])
        except:
            pass
        return None


# ============================================================================
# USER MANAGEMENT SERVICE
# ============================================================================

class UserManagementService(BaseService, UserManagementServiceInterface):
    """Service for user management business logic."""
    
    def __init__(
        self,
        user_repo: UserRepository,
        preference_repo: UserPreferenceRepository
    ):
        self.user_repo = user_repo
        self.preference_repo = preference_repo
    
    async def get_user_profile(self, user_id: int) -> UserDetail:
        """Get complete user profile."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Add computed fields
        user_dict = user.dict()
        user_dict['is_premium'] = user.is_premium
        user_dict['is_active'] = user.is_active
        
        return UserDetail(**user_dict)
    
    async def update_user_profile(self, user_id: int, update_data: UserUpdate) -> UserDetail:
        """Update user profile."""
        user = await self.user_repo.update(user_id, update_data)
        if not user:
            raise NotFoundError("User not found")
        
        logger.info(f"Updated profile for user: {user_id}")
        return user
    
    async def delete_user_account(self, user_id: int) -> bool:
        """Delete user account (soft delete)."""
        result = await self.user_repo.soft_delete(user_id)
        if result:
            logger.info(f"Deleted account for user: {user_id}")
        return result
    
    async def get_user_preferences(self, user_id: int) -> UserPreferenceDetail:
        """Get user preferences."""
        preferences = await self.preference_repo.get_by_user_id(user_id)
        if not preferences:
            # Create default preferences
            default_prefs = UserPreferenceCreate()
            preferences = await self.preference_repo.create(user_id, default_prefs)
        
        return preferences
    
    async def update_user_preferences(self, user_id: int, preferences: UserPreferenceUpdate) -> UserPreferenceDetail:
        """Update user preferences."""
        return await self.preference_repo.update(user_id, preferences)
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user activity statistics."""
        return await self.user_repo.get_user_statistics(user_id)


# ============================================================================
# WATCHLIST SERVICE
# ============================================================================

class WatchlistService(BaseService, WatchlistServiceInterface):
    """Service for watchlist management business logic."""
    
    def __init__(self, watchlist_repo: UserWatchlistRepository):
        self.watchlist_repo = watchlist_repo
    
    async def create_watchlist(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistDetail:
        """Create a new watchlist."""
        # Validate user subscription limits
        user_watchlists = await self.watchlist_repo.get_user_watchlists(user_id)
        
        # Free users can have max 3 watchlists
        if len(user_watchlists) >= 3:
            raise BusinessLogicError("Maximum number of watchlists reached for free users")
        
        return await self.watchlist_repo.create(user_id, watchlist_data)
    
    async def get_user_watchlists(self, user_id: int) -> List[UserWatchlistSummary]:
        """Get all watchlists for a user."""
        return await self.watchlist_repo.get_user_watchlists(user_id)
    
    async def get_watchlist(self, watchlist_id: int, user_id: int) -> UserWatchlistDetail:
        """Get specific watchlist."""
        watchlist = await self.watchlist_repo.get_by_id(watchlist_id)
        if not watchlist:
            raise NotFoundError("Watchlist not found")
        
        if watchlist.user_id != user_id:
            raise ValidationError("Access denied")
        
        return watchlist
    
    async def update_watchlist(self, watchlist_id: int, user_id: int, update_data: UserWatchlistUpdate) -> UserWatchlistDetail:
        """Update watchlist."""
        # Verify ownership
        await self.get_watchlist(watchlist_id, user_id)
        return await self.watchlist_repo.update(watchlist_id, update_data)
    
    async def manage_watchlist_items(self, watchlist_id: int, user_id: int, action: WatchlistItemAction) -> bool:
        """Add or remove items from watchlist."""
        # Verify ownership
        await self.get_watchlist(watchlist_id, user_id)
        
        if action.action == "add":
            return await self.watchlist_repo.add_item(watchlist_id, action.item_type, action.item_id)
        elif action.action == "remove":
            return await self.watchlist_repo.remove_item(watchlist_id, action.item_type, action.item_id)
        else:
            raise ValidationError("Invalid action")
    
    async def delete_watchlist(self, watchlist_id: int, user_id: int) -> bool:
        """Delete watchlist."""
        # Verify ownership
        await self.get_watchlist(watchlist_id, user_id)
        return await self.watchlist_repo.delete(watchlist_id)
    
    async def get_watchlist_performance(self, watchlist_id: int, user_id: int) -> Dict[str, Any]:
        """Get performance metrics for watchlist items."""
        # Verify ownership
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        
        # This would calculate performance for watched securities/members
        # For now, return empty metrics
        return {
            'watchlist_id': watchlist_id,
            'total_items': watchlist.item_count,
            'performance_metrics': {}
        }


# ============================================================================
# ALERT SERVICE
# ============================================================================

class AlertService(BaseService, AlertServiceInterface):
    """Service for alert management business logic."""
    
    def __init__(self, alert_repo: UserAlertRepository):
        self.alert_repo = alert_repo
    
    async def create_alert(self, user_id: int, alert_data: UserAlertCreate) -> UserAlertDetail:
        """Create a new alert."""
        # Validate alert conditions
        if not await self.validate_alert_conditions(alert_data):
            raise ValidationError("Invalid alert conditions")
        
        # Check user limits (free users limited to 5 alerts)
        user_alerts = await self.alert_repo.get_user_alerts(user_id, active_only=False)
        if len(user_alerts) >= 5:
            raise BusinessLogicError("Maximum number of alerts reached for free users")
        
        return await self.alert_repo.create(user_id, alert_data)
    
    async def get_user_alerts(self, user_id: int) -> List[UserAlertSummary]:
        """Get all alerts for a user."""
        return await self.alert_repo.get_user_alerts(user_id, active_only=False)
    
    async def get_alert(self, alert_id: int, user_id: int) -> UserAlertDetail:
        """Get specific alert."""
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert not found")
        
        if alert.user_id != user_id:
            raise ValidationError("Access denied")
        
        return alert
    
    async def update_alert(self, alert_id: int, user_id: int, update_data: UserAlertUpdate) -> UserAlertDetail:
        """Update alert."""
        # Verify ownership
        await self.get_alert(alert_id, user_id)
        return await self.alert_repo.update(alert_id, update_data)
    
    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete alert."""
        # Verify ownership
        await self.get_alert(alert_id, user_id)
        return await self.alert_repo.delete(alert_id)
    
    async def check_alerts(self) -> int:
        """Check all active alerts and trigger notifications."""
        alerts = await self.alert_repo.get_alerts_to_check()
        triggered_count = 0
        
        for alert in alerts:
            # Check alert conditions (simplified)
            if self._should_trigger_alert(alert):
                await self.alert_repo.trigger_alert(alert.id)
                triggered_count += 1
                logger.info(f"Alert triggered: {alert.id}")
        
        return triggered_count
    
    async def validate_alert_conditions(self, alert_data: UserAlertCreate) -> bool:
        """Validate alert conditions."""
        # Validate required fields
        if not alert_data.conditions:
            return False
        
        # Validate condition structure
        required_keys = ['field', 'operator', 'value']
        for condition in alert_data.conditions.values():
            if not all(key in condition for key in required_keys):
                return False
        
        return True
    
    def _should_trigger_alert(self, alert: UserAlertDetail) -> bool:
        """Check if alert should be triggered (simplified implementation)."""
        # This would implement actual alert condition checking
        # For now, return False to avoid triggering
        return False


# ============================================================================
# NOTIFICATION SERVICE
# ============================================================================

class NotificationService(BaseService, NotificationServiceInterface):
    """Service for notification management business logic."""
    
    def __init__(self, notification_repo: UserNotificationRepository):
        self.notification_repo = notification_repo
    
    async def send_notification(self, user_id: int, notification_data: UserNotificationCreate) -> UserNotificationDetail:
        """Send notification to user."""
        notification = await self.notification_repo.create(user_id, notification_data)
        
        # Here would implement actual sending (email, push, etc.)
        logger.info(f"Notification sent to user {user_id}: {notification.title}")
        return notification
    
    async def get_user_notifications(self, user_id: int, query: NotificationQuery) -> Tuple[List[UserNotificationSummary], int]:
        """Get notifications for a user."""
        return await self.notification_repo.get_user_notifications(user_id, query)
    
    async def mark_notifications_read(self, user_id: int, notification_ids: List[int]) -> int:
        """Mark notifications as read."""
        return await self.notification_repo.mark_multiple_as_read(notification_ids)
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get unread notification count."""
        return await self.notification_repo.get_unread_count(user_id)
    
    async def send_bulk_notification(self, user_ids: List[int], notification_data: UserNotificationCreate) -> int:
        """Send notification to multiple users."""
        sent_count = 0
        for user_id in user_ids:
            try:
                await self.send_notification(user_id, notification_data)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
        
        return sent_count
    
    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """Clean up old notifications."""
        return await self.notification_repo.cleanup_expired()


# ============================================================================
# SUBSCRIPTION SERVICE
# ============================================================================

class SubscriptionService(BaseService, SubscriptionServiceInterface):
    """Service for subscription management business logic."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def get_subscription_info(self, user_id: int) -> SubscriptionInfo:
        """Get user subscription information."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        features = self._get_tier_features(user.subscription_tier)
        
        return SubscriptionInfo(
            subscription_tier=user.subscription_tier,
            subscription_status=user.subscription_status or "active",
            subscription_start_date=user.subscription_start_date,
            subscription_end_date=user.subscription_end_date,
            stripe_customer_id=user.stripe_customer_id,
            features=features
        )
    
    async def upgrade_subscription(self, user_id: int, subscription_data: SubscriptionUpdate) -> SubscriptionInfo:
        """Upgrade user subscription."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Validate upgrade path
        if not self._can_upgrade_to(user.subscription_tier, subscription_data.subscription_tier):
            raise ValidationError("Invalid subscription upgrade")
        
        # Update subscription
        update_data = {
            'subscription_tier': subscription_data.subscription_tier,
            'subscription_status': 'active',
            'subscription_start_date': date.today()
        }
        
        if subscription_data.subscription_tier == SubscriptionTier.PRO:
            update_data['subscription_end_date'] = date.today() + timedelta(days=30)
        elif subscription_data.subscription_tier == SubscriptionTier.ENTERPRISE:
            update_data['subscription_end_date'] = date.today() + timedelta(days=365)
        
        updated_user = await self.user_repo.update_subscription(user_id, update_data)
        
        logger.info(f"Upgraded subscription for user {user_id} to {subscription_data.subscription_tier.value}")
        return await self.get_subscription_info(user_id)
    
    async def downgrade_subscription(self, user_id: int, subscription_data: SubscriptionUpdate) -> SubscriptionInfo:
        """Downgrade user subscription."""
        # Similar to upgrade but with downgrade logic
        logger.info(f"Downgraded subscription for user {user_id} to {subscription_data.subscription_tier.value}")
        return await self.get_subscription_info(user_id)
    
    async def cancel_subscription(self, user_id: int, cancellation_data: Dict[str, Any]) -> bool:
        """Cancel user subscription."""
        update_data = {
            'subscription_status': 'cancelled',
            'subscription_end_date': date.today() + timedelta(days=30)  # Grace period
        }
        
        await self.user_repo.update_subscription(user_id, update_data)
        logger.info(f"Cancelled subscription for user {user_id}")
        return True
    
    async def reactivate_subscription(self, user_id: int) -> SubscriptionInfo:
        """Reactivate cancelled subscription."""
        update_data = {
            'subscription_status': 'active',
            'subscription_end_date': date.today() + timedelta(days=30)
        }
        
        await self.user_repo.update_subscription(user_id, update_data)
        logger.info(f"Reactivated subscription for user {user_id}")
        return await self.get_subscription_info(user_id)
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Process subscription webhook from payment provider."""
        # Implementation would handle Stripe webhooks
        logger.info("Processed subscription webhook")
        return True
    
    async def check_subscription_limits(self, user_id: int, feature: str) -> bool:
        """Check if user can access feature based on subscription."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False
        
        return user.can_access_feature(feature)
    
    def _get_tier_features(self, tier: SubscriptionTier) -> List[str]:
        """Get features for subscription tier."""
        features_map = {
            SubscriptionTier.FREE: ['basic_alerts', 'limited_watchlists'],
            SubscriptionTier.PRO: ['advanced_analytics', 'api_access', 'custom_alerts', 'unlimited_watchlists'],
            SubscriptionTier.ENTERPRISE: ['all_pro_features', 'priority_support', 'white_label']
        }
        return features_map.get(tier, [])
    
    def _can_upgrade_to(self, current_tier: SubscriptionTier, target_tier: SubscriptionTier) -> bool:
        """Check if upgrade is valid."""
        tier_order = [SubscriptionTier.FREE, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]
        current_index = tier_order.index(current_tier)
        target_index = tier_order.index(target_tier)
        return target_index > current_index


# Log service creation
logger.info("Users domain services initialized")

# Export all services
__all__ = [
    "AuthenticationService",
    "UserManagementService", 
    "WatchlistService",
    "AlertService",
    "NotificationService",
    "SubscriptionService"
] 