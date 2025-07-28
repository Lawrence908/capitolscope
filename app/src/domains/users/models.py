"""
Users domain database models.

This module contains SQLAlchemy models for user authentication, subscriptions,
preferences, and notification settings.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    BigInteger, ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ARRAY, JSON, Enum
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from domains.base.models import CapitolScopeBaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin
from domains.base.schemas import SubscriptionTier
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class UserStatus(str, PyEnum):
    """User account status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class AuthProvider(str, PyEnum):
    """Authentication provider types."""
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"
    GITHUB = "GITHUB"
    TWITTER = "TWITTER"


class UserRole(str, PyEnum):
    """User role types."""
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class NotificationChannel(str, PyEnum):
    """Notification delivery channels."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"


class NotificationType(str, PyEnum):
    """Types of notifications."""
    TRADE_ALERT = "TRADE_ALERT"
    PORTFOLIO_UPDATE = "PORTFOLIO_UPDATE"
    NEWS_DIGEST = "NEWS_DIGEST"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"
    SUBSCRIPTION_UPDATE = "SUBSCRIPTION_UPDATE"


# ============================================================================
# USER MODELS
# ============================================================================

class User(CapitolScopeBaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Main user model for authentication and profile."""
    
    __tablename__ = 'users'
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, index=True)  # Optional username
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    
    # Authentication
    password_hash = Column(String(255))  # Null for OAuth users
    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.EMAIL)
    provider_id = Column(String(255))  # External provider user ID
    
    # Account Status
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING_VERIFICATION)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    
    # Profile Information
    avatar_url = Column(String(500))
    bio = Column(Text)
    location = Column(String(200))
    website_url = Column(String(500))
    
    # Privacy Settings
    is_public_profile = Column(Boolean, default=True, nullable=False)
    show_portfolio = Column(Boolean, default=False, nullable=False)
    show_trading_activity = Column(Boolean, default=True, nullable=False)
    
    # Subscription Information
    subscription_tier = Column(String(20), nullable=False, default='free')
    subscription_status = Column(String(20), default='active')  # active, canceled, past_due, etc.
    subscription_start_date = Column(Date)
    subscription_end_date = Column(Date)
    stripe_customer_id = Column(String(100), unique=True, index=True)
    
    # Usage Tracking
    api_calls_count = Column(Integer, default=0, nullable=False)
    api_calls_reset_date = Column(Date)
    last_active_at = Column(DateTime(timezone=True))
    
    # Feature Flags
    beta_features_enabled = Column(Boolean, default=False, nullable=False)
    marketing_emails_enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("UserAlert", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    notification_subscriptions = relationship("NotificationSubscription", back_populates="user", cascade="all, delete-orphan")
    newsletter_subscriptions = relationship("NewsletterSubscription", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in UserStatus]),
            name='check_user_status'
        ),
        CheckConstraint(
            auth_provider.in_([p.value for p in AuthProvider]),
            name='check_auth_provider'
        ),
        CheckConstraint(
            role.in_([r.value for r in UserRole]),
            name='check_user_role'
        ),
        CheckConstraint(
            subscription_tier.in_(['free', 'pro', 'premium', 'enterprise']),
            name='check_subscription_tier'
        ),
        Index('idx_user_email_provider', 'email', 'auth_provider'),
        Index('idx_user_subscription', 'subscription_tier', 'subscription_status'),
        Index('idx_user_status_verified', 'status', 'is_verified'),
        Index('idx_user_role', 'role'),
    )
    
    def __repr__(self):
        return f"<User(email={self.email}, status={self.status.value})>"
    
    @property
    def display_name(self) -> str:
        """Return the best display name for the user."""
        if self.full_name:
            return self.full_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.username:
            return self.username
        else:
            return self.email.split('@')[0]
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription."""
        return self.subscription_tier in ['pro', 'premium', 'enterprise']

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_deleted

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]

    @property
    def is_moderator(self) -> bool:
        """Check if user has moderator role or higher."""
        return self.role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]

    @property
    def is_super_admin(self) -> bool:
        """Check if user has super admin role."""
        return self.role == UserRole.SUPER_ADMIN

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission based on role."""
        role_permissions = {
            UserRole.USER: [
                'read:own_profile', 'update:own_profile', 
                'read:trades', 'read:members', 'create:watchlist',
                'read:market_data'
            ],
            UserRole.MODERATOR: [
                'read:own_profile', 'update:own_profile', 
                'read:trades', 'read:members', 'create:watchlist',
                'read:market_data', 'moderate:discussions',
                'delete:inappropriate_content'
            ],
            UserRole.ADMIN: [
                'read:own_profile', 'update:own_profile', 
                'read:trades', 'read:members', 'create:watchlist',
                'read:market_data', 'moderate:discussions',
                'delete:inappropriate_content', 'read:all_users',
                'update:user_roles', 'read:system_metrics',
                'manage:notifications'
            ],
            UserRole.SUPER_ADMIN: ['*']  # All permissions
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return '*' in user_permissions or permission in user_permissions

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.has_permission('update:user_roles')

    def can_access_admin_panel(self) -> bool:
        """Check if user can access admin panel."""
        return self.is_admin or self.is_super_admin

    def can_access_feature(self, feature: str) -> bool:
        """Check if user can access a specific feature based on subscription."""
        feature_tiers = {
            'advanced_analytics': ['pro', 'premium', 'enterprise'],
            'api_access': ['pro', 'premium', 'enterprise'],
            'custom_alerts': ['pro', 'premium', 'enterprise'],
            'unlimited_watchlists': ['pro', 'premium', 'enterprise'],
            'export_data': ['pro', 'premium', 'enterprise'],
            'priority_support': ['enterprise'],
            'white_label': ['enterprise']
        }
        
        required_tiers = feature_tiers.get(feature, [])
        return self.subscription_tier in required_tiers or not required_tiers
    
    def update_last_active(self):
        """Update last active timestamp."""
        self.last_active_at = func.now()


# ============================================================================
# USER PREFERENCES
# ============================================================================

class UserPreference(CapitolScopeBaseModel, TimestampMixin):
    """User preferences and settings."""
    
    __tablename__ = 'user_preferences'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Display Preferences
    theme = Column(String(20), default='dark')  # light, dark, auto
    language = Column(String(5), default='en')
    timezone = Column(String(50), default='UTC')
    currency = Column(String(3), default='USD')
    
    # Trading Preferences
    default_trade_filters = Column(JSONB)  # Saved filter preferences
    preferred_chart_timeframe = Column(String(10), default='1D')
    show_after_hours_trading = Column(Boolean, default=True)
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    
    # Alert Thresholds
    large_trade_threshold = Column(BigInteger, default=100000000)  # $1M in cents
    price_movement_threshold = Column(Integer, default=500)  # 5% in basis points
    
    # Privacy Preferences
    public_watchlists = Column(Boolean, default=False)
    share_analytics = Column(Boolean, default=True)
    
    # Custom Settings (JSON)
    custom_settings = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', name='unique_user_preferences'),
        Index('idx_user_preference_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id}, theme={self.theme})>"


# ============================================================================
# USER WATCHLISTS
# ============================================================================

class UserWatchlist(CapitolScopeBaseModel, TimestampMixin):
    """User-created watchlists for tracking securities or members."""
    
    __tablename__ = 'user_watchlists'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Watchlist Type
    watchlist_type = Column(String(20), nullable=False, default='securities')  # securities, members, mixed
    
    # Settings
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Watched Items (JSONB for flexibility)
    watched_securities = Column(JSONB, default=list)  # List of security IDs
    watched_members = Column(JSONB, default=list)  # List of member IDs
    
    # Metadata
    item_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            watchlist_type.in_(['securities', 'members', 'mixed']),
            name='check_watchlist_type'
        ),
        Index('idx_user_watchlist_user_type', 'user_id', 'watchlist_type'),
        Index('idx_user_watchlist_public', 'is_public'),
    )
    
    def __repr__(self):
        return f"<UserWatchlist(name={self.name}, user_id={self.user_id})>"
    
    def add_security(self, security_id: int):
        """Add a security to the watchlist."""
        if self.watched_securities is None:
            self.watched_securities = []
        if security_id not in self.watched_securities:
            self.watched_securities.append(security_id)
            self.item_count = len(self.watched_securities) + len(self.watched_members or [])
            self.last_updated = func.now()
    
    def remove_security(self, security_id: int):
        """Remove a security from the watchlist."""
        if self.watched_securities and security_id in self.watched_securities:
            self.watched_securities.remove(security_id)
            self.item_count = len(self.watched_securities) + len(self.watched_members or [])
            self.last_updated = func.now()
    
    def add_member(self, member_id: int):
        """Add a congress member to the watchlist."""
        if self.watched_members is None:
            self.watched_members = []
        if member_id not in self.watched_members:
            self.watched_members.append(member_id)
            self.item_count = len(self.watched_securities or []) + len(self.watched_members)
            self.last_updated = func.now()
    
    def remove_member(self, member_id: int):
        """Remove a congress member from the watchlist."""
        if self.watched_members and member_id in self.watched_members:
            self.watched_members.remove(member_id)
            self.item_count = len(self.watched_securities or []) + len(self.watched_members)
            self.last_updated = func.now()


# ============================================================================
# USER ALERTS
# ============================================================================

class UserAlert(CapitolScopeBaseModel, TimestampMixin):
    """User-configured alerts for trading activity and price movements."""
    
    __tablename__ = 'user_alerts'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Alert Configuration
    name = Column(String(100), nullable=False)
    description = Column(Text)
    alert_type = Column(String(30), nullable=False)  # new_trade, large_trade, price_movement, etc.
    
    # Target Configuration
    target_type = Column(String(20))  # security, member, portfolio, market
    target_id = Column(Integer)  # ID of target entity
    target_criteria = Column(JSONB)  # Additional criteria as JSON
    
    # Trigger Conditions
    conditions = Column(JSONB, nullable=False)  # Alert conditions as JSON
    threshold_value = Column(BigInteger)  # Threshold value in appropriate units
    comparison_operator = Column(String(10))  # >, <, >=, <=, =, !=
    
    # Alert Settings
    is_active = Column(Boolean, default=True, nullable=False)
    notification_channels = Column(ARRAY(String))  # email, sms, push, in_app
    frequency_limit = Column(String(20), default='immediate')  # immediate, hourly, daily
    
    # Tracking
    last_triggered = Column(DateTime(timezone=True))
    trigger_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            alert_type.in_([
                'new_trade', 'large_trade', 'price_movement', 'volume_spike',
                'portfolio_change', 'member_activity', 'market_event'
            ]),
            name='check_alert_type'
        ),
        CheckConstraint(
            target_type.in_(['security', 'member', 'portfolio', 'market']),
            name='check_target_type'
        ),
        CheckConstraint(
            comparison_operator.in_(['>', '<', '>=', '<=', '=', '!=']),
            name='check_comparison_operator'
        ),
        Index('idx_user_alert_user_active', 'user_id', 'is_active'),
        Index('idx_user_alert_type_target', 'alert_type', 'target_type'),
    )
    
    def __repr__(self):
        return f"<UserAlert(name={self.name}, user_id={self.user_id}, active={self.is_active})>"
    
    def trigger_alert(self):
        """Record that the alert was triggered."""
        self.last_triggered = func.now()
        self.trigger_count += 1


# ============================================================================
# USER NOTIFICATIONS
# ============================================================================

class UserNotification(CapitolScopeBaseModel, TimestampMixin):
    """Individual notifications sent to users."""
    
    __tablename__ = 'user_notifications'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Notification Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    
    # Delivery Information
    channel = Column(Enum(NotificationChannel), nullable=False)
    priority = Column(String(10), default='normal')  # low, normal, high, urgent
    
    # Status Tracking
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    delivery_status = Column(String(20), default='pending')  # pending, sent, delivered, failed
    
    # Related Data
    related_entity_type = Column(String(20))  # trade, member, security, etc.
    related_entity_id = Column(Integer)
    extra_data = Column(JSONB)  # Additional notification data
    
    # Expiration
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            notification_type.in_([t.value for t in NotificationType]),
            name='check_notification_type'
        ),
        CheckConstraint(
            channel.in_([c.value for c in NotificationChannel]),
            name='check_notification_channel'
        ),
        CheckConstraint(
            priority.in_(['low', 'normal', 'high', 'urgent']),
            name='check_notification_priority'
        ),
        CheckConstraint(
            delivery_status.in_(['pending', 'sent', 'delivered', 'failed']),
            name='check_delivery_status'
        ),
        Index('idx_user_notification_user_read', 'user_id', 'is_read'),
        Index('idx_user_notification_type_priority', 'notification_type', 'priority'),
        Index('idx_user_notification_delivery', 'delivery_status', 'sent_at'),
    )
    
    def __repr__(self):
        return f"<UserNotification(title={self.title}, user_id={self.user_id}, read={self.is_read})>"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = func.now()


# ============================================================================
# USER SESSIONS
# ============================================================================

class UserSession(CapitolScopeBaseModel, TimestampMixin):
    """User session tracking for security and analytics."""
    
    __tablename__ = 'user_sessions'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session Information
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    device_type = Column(String(20))  # desktop, mobile, tablet
    browser = Column(String(50))
    os = Column(String(50))
    
    # Location (optional)
    country = Column(String(2))
    city = Column(String(100))
    
    # Session Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Security
    login_method = Column(String(20))  # password, oauth, api_key
    is_suspicious = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            device_type.in_(['desktop', 'mobile', 'tablet', 'api', 'unknown']),
            name='check_device_type'
        ),
        CheckConstraint(
            login_method.in_(['password', 'oauth', 'api_key', 'token']),
            name='check_login_method'
        ),
        Index('idx_user_session_user_active', 'user_id', 'is_active'),
        Index('idx_user_session_expires', 'expires_at'),
        Index('idx_user_session_suspicious', 'is_suspicious'),
    )
    
    def __repr__(self):
        return f"<UserSession(session_id={self.session_id[:8]}..., user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def extend_session(self, hours: int = 24):
        """Extend session expiration."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.last_activity = func.now()


# ============================================================================
# API KEYS (For Premium Users)
# ============================================================================

class UserApiKey(CapitolScopeBaseModel, TimestampMixin):
    """API keys for premium users."""
    
    __tablename__ = 'user_api_keys'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Key Information
    key_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Permissions
    scopes = Column(ARRAY(String))  # read:trades, read:members, write:watchlists, etc.
    
    # Usage Limits
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(BigInteger, default=0, nullable=False)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        Index('idx_user_api_key_user_active', 'user_id', 'is_active'),
        Index('idx_user_api_key_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserApiKey(name={self.name}, user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def record_usage(self):
        """Record API key usage."""
        self.last_used_at = func.now()
        self.usage_count += 1


# ============================================================================
# PASSWORD RESET TOKENS
# ============================================================================

class PasswordResetToken(CapitolScopeBaseModel, TimestampMixin):
    """Password reset tokens for secure password recovery."""
    
    __tablename__ = 'password_reset_tokens'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    
    # Token Information
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True))
    is_used = Column(Boolean, default=False, nullable=False)
    
    # Security
    ip_address = Column(String(45))  # IP address where token was requested
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        Index('ix_password_reset_tokens_user_expires', 'user_id', 'expires_at'),
        Index('ix_password_reset_tokens_token_hash', 'token_hash'),
    )
    
    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, expires_at={self.expires_at})>"
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid and not used."""
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)
        return self


# Log model creation
logger.info("Users domain models initialized")

# Export all models
__all__ = [
    "User",
    "UserPreference", 
    "UserWatchlist",
    "UserAlert",
    "UserNotification",
    "UserSession",
    "UserApiKey",
    "PasswordResetToken",
    # Enums
    "UserStatus",
    "UserRole",
    "AuthProvider", 
    "NotificationChannel",
    "NotificationType"
] 