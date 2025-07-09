"""
Users domain Pydantic schemas.

This module contains request/response schemas for user authentication,
subscriptions, preferences, and notifications.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid

from pydantic import BaseModel, Field, EmailStr, validator, root_validator
from pydantic.types import NonNegativeInt, PositiveInt

from domains.base.schemas import (
    CapitolScopeBaseSchema, PaginatedResponse, ResponseMetadata, 
    TimestampMixin, SubscriptionTier
)
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class AuthProvider(str, Enum):
    """Authentication provider types."""
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    TWITTER = "twitter"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationType(str, Enum):
    """Types of notifications."""
    TRADE_ALERT = "trade_alert"
    PORTFOLIO_UPDATE = "portfolio_update"
    NEWS_DIGEST = "news_digest"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SUBSCRIPTION_UPDATE = "subscription_update"


class WatchlistType(str, Enum):
    """Watchlist types."""
    SECURITIES = "securities"
    MEMBERS = "members"
    MIXED = "mixed"


class AlertType(str, Enum):
    """Alert types."""
    NEW_TRADE = "new_trade"
    LARGE_TRADE = "large_trade"
    PRICE_MOVEMENT = "price_movement"
    VOLUME_SPIKE = "volume_spike"
    PORTFOLIO_CHANGE = "portfolio_change"
    MEMBER_ACTIVITY = "member_activity"
    MARKET_EVENT = "market_event"


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(CapitolScopeBaseSchema):
    """Base user schema."""
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)
    auth_provider: AuthProvider = AuthProvider.EMAIL
    marketing_emails_enabled: bool = True
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(CapitolScopeBaseSchema):
    """Schema for updating user profile."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    website_url: Optional[str] = Field(None, max_length=500)
    is_public_profile: Optional[bool] = None
    show_portfolio: Optional[bool] = None
    show_trading_activity: Optional[bool] = None


class UserLogin(CapitolScopeBaseSchema):
    """Schema for user login."""
    email: EmailStr
    password: str
    remember_me: bool = False


class UserOAuthLogin(CapitolScopeBaseSchema):
    """Schema for OAuth login."""
    auth_provider: AuthProvider
    provider_token: str
    provider_id: str


class PasswordChange(CapitolScopeBaseSchema):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordReset(CapitolScopeBaseSchema):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(CapitolScopeBaseSchema):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserSummary(UserBase, TimestampMixin):
    """Summary user schema for list views."""
    id: int
    full_name: Optional[str] = None
    status: UserStatus
    is_verified: bool
    subscription_tier: SubscriptionTier
    avatar_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class UserDetail(UserSummary):
    """Detailed user schema."""
    provider_id: Optional[str] = None
    auth_provider: AuthProvider
    bio: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None
    email_verified_at: Optional[datetime] = None
    subscription_status: Optional[str] = None
    subscription_start_date: Optional[date] = None
    subscription_end_date: Optional[date] = None
    is_public_profile: bool
    show_portfolio: bool
    show_trading_activity: bool
    beta_features_enabled: bool
    marketing_emails_enabled: bool
    last_active_at: Optional[datetime] = None
    
    # Computed fields
    is_premium: Optional[bool] = None
    is_active: Optional[bool] = None


class UserProfile(UserDetail):
    """User profile with additional statistics."""
    watchlist_count: Optional[int] = None
    alert_count: Optional[int] = None
    notification_count: Optional[int] = None
    api_calls_count: Optional[int] = None


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class TokenResponse(CapitolScopeBaseSchema):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenRefresh(CapitolScopeBaseSchema):
    """Token refresh schema."""
    refresh_token: str


class SessionInfo(CapitolScopeBaseSchema):
    """Current session information."""
    session_id: str
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    last_activity: datetime
    expires_at: datetime
    
    class Config:
        orm_mode = True


# ============================================================================
# PREFERENCE SCHEMAS
# ============================================================================

class UserPreferenceBase(CapitolScopeBaseSchema):
    """Base user preference schema."""
    theme: str = Field("light", regex="^(light|dark|auto)$")
    language: str = Field("en", min_length=2, max_length=5)
    timezone: str = Field("UTC", max_length=50)
    currency: str = Field("USD", min_length=3, max_length=3)


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences."""
    default_trade_filters: Optional[Dict[str, Any]] = None
    preferred_chart_timeframe: str = Field("1D", max_length=10)
    show_after_hours_trading: bool = True
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    large_trade_threshold: int = Field(100000000, ge=0)  # $1M in cents
    price_movement_threshold: int = Field(500, ge=0, le=10000)  # 5% in basis points
    public_watchlists: bool = False
    share_analytics: bool = True
    custom_settings: Optional[Dict[str, Any]] = None


class UserPreferenceUpdate(CapitolScopeBaseSchema):
    """Schema for updating user preferences."""
    theme: Optional[str] = Field(None, regex="^(light|dark|auto)$")
    language: Optional[str] = Field(None, min_length=2, max_length=5)
    timezone: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    default_trade_filters: Optional[Dict[str, Any]] = None
    preferred_chart_timeframe: Optional[str] = Field(None, max_length=10)
    show_after_hours_trading: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    large_trade_threshold: Optional[int] = Field(None, ge=0)
    price_movement_threshold: Optional[int] = Field(None, ge=0, le=10000)
    public_watchlists: Optional[bool] = None
    share_analytics: Optional[bool] = None
    custom_settings: Optional[Dict[str, Any]] = None


class UserPreferenceDetail(UserPreferenceBase, TimestampMixin):
    """Detailed user preference schema."""
    id: int
    user_id: int
    default_trade_filters: Optional[Dict[str, Any]] = None
    preferred_chart_timeframe: str
    show_after_hours_trading: bool
    email_notifications: bool
    push_notifications: bool
    sms_notifications: bool
    large_trade_threshold: int
    price_movement_threshold: int
    public_watchlists: bool
    share_analytics: bool
    custom_settings: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


# ============================================================================
# WATCHLIST SCHEMAS
# ============================================================================

class UserWatchlistBase(CapitolScopeBaseSchema):
    """Base watchlist schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    watchlist_type: WatchlistType = WatchlistType.SECURITIES
    is_public: bool = False


class UserWatchlistCreate(UserWatchlistBase):
    """Schema for creating a watchlist."""
    is_default: bool = False
    watched_securities: Optional[List[int]] = None
    watched_members: Optional[List[int]] = None


class UserWatchlistUpdate(CapitolScopeBaseSchema):
    """Schema for updating a watchlist."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    is_default: Optional[bool] = None


class WatchlistItemAction(CapitolScopeBaseSchema):
    """Schema for adding/removing watchlist items."""
    item_type: str = Field(..., regex="^(security|member)$")
    item_id: int = Field(..., gt=0)
    action: str = Field(..., regex="^(add|remove)$")


class UserWatchlistSummary(UserWatchlistBase, TimestampMixin):
    """Summary watchlist schema."""
    id: int
    user_id: int
    item_count: int
    is_default: bool
    sort_order: int
    last_updated: datetime
    
    class Config:
        orm_mode = True


class UserWatchlistDetail(UserWatchlistSummary):
    """Detailed watchlist schema."""
    watched_securities: Optional[List[int]] = None
    watched_members: Optional[List[int]] = None


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class UserAlertBase(CapitolScopeBaseSchema):
    """Base alert schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    alert_type: AlertType
    target_type: Optional[str] = Field(None, regex="^(security|member|portfolio|market)$")
    target_id: Optional[int] = Field(None, gt=0)


class UserAlertCreate(UserAlertBase):
    """Schema for creating an alert."""
    target_criteria: Optional[Dict[str, Any]] = None
    conditions: Dict[str, Any] = Field(..., min_items=1)
    threshold_value: Optional[int] = None
    comparison_operator: Optional[str] = Field(None, regex="^(>|<|>=|<=|=|!=)$")
    notification_channels: List[NotificationChannel] = [NotificationChannel.EMAIL]
    frequency_limit: str = Field("immediate", regex="^(immediate|hourly|daily)$")
    is_active: bool = True


class UserAlertUpdate(CapitolScopeBaseSchema):
    """Schema for updating an alert."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    target_criteria: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    threshold_value: Optional[int] = None
    comparison_operator: Optional[str] = Field(None, regex="^(>|<|>=|<=|=|!=)$")
    notification_channels: Optional[List[NotificationChannel]] = None
    frequency_limit: Optional[str] = Field(None, regex="^(immediate|hourly|daily)$")
    is_active: Optional[bool] = None


class UserAlertSummary(UserAlertBase, TimestampMixin):
    """Summary alert schema."""
    id: int
    user_id: int
    is_active: bool
    notification_channels: List[str]
    frequency_limit: str
    last_triggered: Optional[datetime] = None
    trigger_count: int
    
    class Config:
        orm_mode = True


class UserAlertDetail(UserAlertSummary):
    """Detailed alert schema."""
    target_criteria: Optional[Dict[str, Any]] = None
    conditions: Dict[str, Any]
    threshold_value: Optional[int] = None
    comparison_operator: Optional[str] = None


# ============================================================================
# NOTIFICATION SCHEMAS
# ============================================================================

class UserNotificationBase(CapitolScopeBaseSchema):
    """Base notification schema."""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    notification_type: NotificationType
    channel: NotificationChannel
    priority: str = Field("normal", regex="^(low|normal|high|urgent)$")


class UserNotificationCreate(UserNotificationBase):
    """Schema for creating a notification."""
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class UserNotificationSummary(UserNotificationBase, TimestampMixin):
    """Summary notification schema."""
    id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivery_status: str
    expires_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class UserNotificationDetail(UserNotificationSummary):
    """Detailed notification schema."""
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationMarkRead(CapitolScopeBaseSchema):
    """Schema for marking notifications as read."""
    notification_ids: List[int] = Field(..., min_items=1)


# ============================================================================
# SUBSCRIPTION SCHEMAS
# ============================================================================

class SubscriptionUpdate(CapitolScopeBaseSchema):
    """Schema for updating subscription."""
    subscription_tier: SubscriptionTier
    payment_method_id: Optional[str] = None


class SubscriptionCancel(CapitolScopeBaseSchema):
    """Schema for canceling subscription."""
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    feedback: Optional[str] = Field(None, max_length=1000)


class SubscriptionInfo(CapitolScopeBaseSchema):
    """Subscription information schema."""
    subscription_tier: SubscriptionTier
    subscription_status: str
    subscription_start_date: Optional[date] = None
    subscription_end_date: Optional[date] = None
    stripe_customer_id: Optional[str] = None
    next_billing_date: Optional[date] = None
    amount: Optional[int] = None  # In cents
    currency: str = "USD"
    features: List[str] = []
    
    class Config:
        orm_mode = True


# ============================================================================
# API KEY SCHEMAS
# ============================================================================

class ApiKeyCreate(CapitolScopeBaseSchema):
    """Schema for creating API key."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scopes: List[str] = Field(..., min_items=1)
    rate_limit_per_hour: int = Field(1000, ge=1, le=10000)
    rate_limit_per_day: int = Field(10000, ge=1, le=100000)
    expires_at: Optional[datetime] = None


class ApiKeyUpdate(CapitolScopeBaseSchema):
    """Schema for updating API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scopes: Optional[List[str]] = None
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=100000)
    is_active: Optional[bool] = None


class ApiKeySummary(CapitolScopeBaseSchema):
    """Summary API key schema."""
    id: str  # UUID as string
    name: str
    description: Optional[str] = None
    scopes: List[str]
    is_active: bool
    rate_limit_per_hour: int
    rate_limit_per_day: int
    last_used_at: Optional[datetime] = None
    usage_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        orm_mode = True


class ApiKeyDetail(ApiKeySummary):
    """Detailed API key schema with secret."""
    api_key: str  # Only returned when first created


# ============================================================================
# QUERY SCHEMAS
# ============================================================================

class UserQuery(CapitolScopeBaseSchema):
    """Query parameters for users."""
    status: Optional[List[UserStatus]] = None
    subscription_tiers: Optional[List[SubscriptionTier]] = None
    auth_providers: Optional[List[AuthProvider]] = None
    is_verified: Optional[bool] = None
    search: Optional[str] = Field(None, min_length=1)
    sort_by: str = "created_at"
    sort_order: str = Field("desc", regex="^(asc|desc)$")
    page: PositiveInt = 1
    limit: int = Field(50, ge=1, le=1000)


class NotificationQuery(CapitolScopeBaseSchema):
    """Query parameters for notifications."""
    notification_types: Optional[List[NotificationType]] = None
    channels: Optional[List[NotificationChannel]] = None
    is_read: Optional[bool] = None
    priority: Optional[str] = Field(None, regex="^(low|normal|high|urgent)$")
    sort_by: str = "created_at"
    sort_order: str = Field("desc", regex="^(asc|desc)$")
    page: PositiveInt = 1
    limit: int = Field(50, ge=1, le=1000)


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class UserListResponse(PaginatedResponse):
    """Response schema for user list."""
    data: List[UserSummary]


class UserDetailResponse(CapitolScopeBaseSchema):
    """Response schema for user detail."""
    data: UserDetail
    metadata: ResponseMetadata


class WatchlistListResponse(PaginatedResponse):
    """Response schema for watchlist list."""
    data: List[UserWatchlistSummary]


class AlertListResponse(PaginatedResponse):
    """Response schema for alert list."""
    data: List[UserAlertSummary]


class NotificationListResponse(PaginatedResponse):
    """Response schema for notification list."""
    data: List[UserNotificationSummary]


class ApiKeyListResponse(PaginatedResponse):
    """Response schema for API key list."""
    data: List[ApiKeySummary]


# Log schema creation
logger.info("Users domain schemas initialized")

# Export all schemas
__all__ = [
    # Enums
    "UserStatus", "AuthProvider", "NotificationChannel", "NotificationType", 
    "WatchlistType", "AlertType",
    
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserLogin", "UserOAuthLogin",
    "PasswordChange", "PasswordReset", "PasswordResetConfirm",
    "UserSummary", "UserDetail", "UserProfile",
    
    # Auth schemas
    "TokenResponse", "TokenRefresh", "SessionInfo",
    
    # Preference schemas
    "UserPreferenceBase", "UserPreferenceCreate", "UserPreferenceUpdate", "UserPreferenceDetail",
    
    # Watchlist schemas
    "UserWatchlistBase", "UserWatchlistCreate", "UserWatchlistUpdate", "WatchlistItemAction",
    "UserWatchlistSummary", "UserWatchlistDetail",
    
    # Alert schemas
    "UserAlertBase", "UserAlertCreate", "UserAlertUpdate", "UserAlertSummary", "UserAlertDetail",
    
    # Notification schemas
    "UserNotificationBase", "UserNotificationCreate", "UserNotificationSummary", 
    "UserNotificationDetail", "NotificationMarkRead",
    
    # Subscription schemas
    "SubscriptionUpdate", "SubscriptionCancel", "SubscriptionInfo",
    
    # API Key schemas
    "ApiKeyCreate", "ApiKeyUpdate", "ApiKeySummary", "ApiKeyDetail",
    
    # Query schemas
    "UserQuery", "NotificationQuery",
    
    # Response schemas
    "UserListResponse", "UserDetailResponse", "WatchlistListResponse", 
    "AlertListResponse", "NotificationListResponse", "ApiKeyListResponse"
] 