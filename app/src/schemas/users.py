"""
User management, authentication, and subscription Pydantic schemas.

This module contains all schemas related to users, authentication,
subscriptions, and user preferences for the CapitolScope API.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import Field, field_validator, EmailStr, HttpUrl

from schemas.base import (
    CapitolScopeBaseModel, IDMixin, UUIDMixin, TimestampMixin,
    SubscriptionTier, SubscriptionStatus, SocialPlatform,
    NotificationPreferences
)


# ============================================================================
# USER AUTHENTICATION
# ============================================================================

class UserBase(CapitolScopeBaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="Full name", max_length=200)
    username: Optional[str] = Field(None, description="Username", max_length=50)
    
    # Profile information
    bio: Optional[str] = Field(None, description="User bio", max_length=500)
    location: Optional[str] = Field(None, description="Location", max_length=100)
    website: Optional[HttpUrl] = Field(None, description="Personal website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar image URL")
    
    # Account settings
    is_active: bool = Field(True, description="Account active status")
    is_verified: bool = Field(False, description="Email verification status")
    
    # Preferences
    timezone: str = Field("UTC", description="User timezone", max_length=50)
    newsletter_subscribed: bool = Field(True, description="Newsletter subscription")
    
    # Privacy settings
    profile_public: bool = Field(True, description="Public profile visibility")
    show_email: bool = Field(False, description="Show email in profile")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserCreate(UserBase):
    """Schema for creating users."""
    # Optional password for local registration
    password: Optional[str] = Field(None, description="Password", min_length=8)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(CapitolScopeBaseModel):
    """Schema for updating users."""
    full_name: Optional[str] = Field(None, description="Full name", max_length=200)
    username: Optional[str] = Field(None, description="Username", max_length=50)
    bio: Optional[str] = Field(None, description="User bio", max_length=500)
    location: Optional[str] = Field(None, description="Location", max_length=100)
    website: Optional[HttpUrl] = Field(None, description="Personal website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar image URL")
    timezone: Optional[str] = Field(None, description="User timezone", max_length=50)
    newsletter_subscribed: Optional[bool] = Field(None, description="Newsletter subscription")
    profile_public: Optional[bool] = Field(None, description="Public profile visibility")
    show_email: Optional[bool] = Field(None, description="Show email in profile")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserResponse(UserBase, UUIDMixin, TimestampMixin):
    """Schema for user responses."""
    # Authentication info
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(0, description="Total login count", ge=0)
    
    # Subscription info
    subscription: Optional["UserSubscriptionResponse"] = Field(None, description="User subscription")
    
    # Social connections
    social_connections: Optional[List["SocialConnectionResponse"]] = Field(None, description="Social connections")
    
    # Statistics
    watchlist_count: Optional[int] = Field(None, description="Watchlist item count", ge=0)
    portfolio_count: Optional[int] = Field(None, description="Portfolio count", ge=0)
    
    # Exclude sensitive fields
    class Config:
        exclude = {"password"}


class UserProfile(CapitolScopeBaseModel):
    """Public user profile schema."""
    id: uuid.UUID = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    bio: Optional[str] = Field(None, description="User bio")
    location: Optional[str] = Field(None, description="Location")
    website: Optional[HttpUrl] = Field(None, description="Website URL")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar URL")
    
    # Conditional fields based on privacy settings
    email: Optional[EmailStr] = Field(None, description="Email if public")
    
    # Public statistics
    member_since: datetime = Field(..., description="Member since date")
    portfolio_count: Optional[int] = Field(None, description="Portfolio count")
    watchlist_count: Optional[int] = Field(None, description="Watchlist count")


class UserSummary(CapitolScopeBaseModel):
    """Lightweight user summary for lists."""
    id: uuid.UUID = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar URL")


# ============================================================================
# AUTHENTICATION
# ============================================================================

class LoginRequest(CapitolScopeBaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password", min_length=1)
    remember_me: bool = Field(False, description="Remember me option")


class LoginResponse(CapitolScopeBaseModel):
    """Login response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class RefreshTokenRequest(CapitolScopeBaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(CapitolScopeBaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(CapitolScopeBaseModel):
    """Password reset confirmation schema."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., description="New password", min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class PasswordChangeRequest(CapitolScopeBaseModel):
    """Password change request schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password", min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class EmailVerificationRequest(CapitolScopeBaseModel):
    """Email verification request schema."""
    token: str = Field(..., description="Verification token")


# ============================================================================
# SOCIAL CONNECTIONS
# ============================================================================

class SocialConnectionBase(CapitolScopeBaseModel):
    """Base social connection schema."""
    platform: SocialPlatform = Field(..., description="Social platform")
    platform_user_id: str = Field(..., description="Platform user ID", max_length=200)
    platform_username: Optional[str] = Field(None, description="Platform username", max_length=100)
    
    # OAuth tokens
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration")
    
    # Connection settings
    is_active: bool = Field(True, description="Connection active status")
    auto_post: bool = Field(False, description="Auto-post enabled")
    
    # Platform-specific settings
    settings: Optional[Dict[str, Any]] = Field(None, description="Platform-specific settings")
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        """Validate social platform."""
        valid_platforms = ['twitter', 'linkedin', 'discord', 'telegram', 'reddit', 'facebook']
        if v not in valid_platforms:
            raise ValueError(f'Platform must be one of: {valid_platforms}')
        return v


class SocialConnectionCreate(SocialConnectionBase):
    """Schema for creating social connections."""
    user_id: uuid.UUID = Field(..., description="User ID")


class SocialConnectionUpdate(CapitolScopeBaseModel):
    """Schema for updating social connections."""
    platform_username: Optional[str] = Field(None, description="Platform username", max_length=100)
    is_active: Optional[bool] = Field(None, description="Connection active status")
    auto_post: Optional[bool] = Field(None, description="Auto-post enabled")
    settings: Optional[Dict[str, Any]] = Field(None, description="Platform-specific settings")


class SocialConnectionResponse(SocialConnectionBase, IDMixin, TimestampMixin):
    """Schema for social connection responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Usage statistics
    posts_count: Optional[int] = Field(None, description="Number of posts made", ge=0)
    last_post_at: Optional[datetime] = Field(None, description="Last post timestamp")
    
    # Connection health
    is_healthy: bool = Field(True, description="Connection health status")
    last_error: Optional[str] = Field(None, description="Last error message")
    
    # Exclude sensitive fields
    class Config:
        exclude = {"access_token", "refresh_token"}


# ============================================================================
# SUBSCRIPTIONS
# ============================================================================

class UserSubscriptionBase(CapitolScopeBaseModel):
    """Base user subscription schema."""
    tier: SubscriptionTier = Field(..., description="Subscription tier")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    
    # Billing information
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID", max_length=100)
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID", max_length=100)
    
    # Subscription period
    current_period_start: Optional[datetime] = Field(None, description="Current period start")
    current_period_end: Optional[datetime] = Field(None, description="Current period end")
    
    # Trial information
    trial_start: Optional[datetime] = Field(None, description="Trial start date")
    trial_end: Optional[datetime] = Field(None, description="Trial end date")
    
    # Cancellation
    cancel_at_period_end: bool = Field(False, description="Cancel at period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    
    # Usage tracking
    api_calls_count: int = Field(0, description="API calls this period", ge=0)
    api_calls_limit: Optional[int] = Field(None, description="API calls limit", ge=0)
    
    # Features
    features: Optional[Dict[str, Any]] = Field(None, description="Enabled features")
    
    @field_validator('tier')
    @classmethod
    def validate_tier(cls, v):
        """Validate subscription tier."""
        valid_tiers = ['free', 'pro', 'premium', 'enterprise']
        if v not in valid_tiers:
            raise ValueError(f'Tier must be one of: {valid_tiers}')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate subscription status."""
        valid_statuses = ['active', 'cancelled', 'expired', 'past_due']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class UserSubscriptionCreate(UserSubscriptionBase):
    """Schema for creating user subscriptions."""
    user_id: uuid.UUID = Field(..., description="User ID")


class UserSubscriptionUpdate(CapitolScopeBaseModel):
    """Schema for updating user subscriptions."""
    tier: Optional[SubscriptionTier] = Field(None, description="Subscription tier")
    status: Optional[SubscriptionStatus] = Field(None, description="Subscription status")
    current_period_start: Optional[datetime] = Field(None, description="Current period start")
    current_period_end: Optional[datetime] = Field(None, description="Current period end")
    trial_start: Optional[datetime] = Field(None, description="Trial start date")
    trial_end: Optional[datetime] = Field(None, description="Trial end date")
    cancel_at_period_end: Optional[bool] = Field(None, description="Cancel at period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    api_calls_count: Optional[int] = Field(None, description="API calls count", ge=0)
    api_calls_limit: Optional[int] = Field(None, description="API calls limit", ge=0)
    features: Optional[Dict[str, Any]] = Field(None, description="Enabled features")


class UserSubscriptionResponse(UserSubscriptionBase, IDMixin, TimestampMixin):
    """Schema for user subscription responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Calculated fields
    is_trial: bool = Field(False, description="Currently in trial period")
    is_active: bool = Field(False, description="Subscription is active")
    days_until_renewal: Optional[int] = Field(None, description="Days until renewal")
    usage_percentage: Optional[float] = Field(None, description="API usage percentage")


class SubscriptionPlan(CapitolScopeBaseModel):
    """Subscription plan information."""
    tier: SubscriptionTier = Field(..., description="Plan tier")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    
    # Pricing
    price_monthly: int = Field(..., description="Monthly price in cents", ge=0)
    price_yearly: int = Field(..., description="Yearly price in cents", ge=0)
    
    # Limits
    api_calls_limit: Optional[int] = Field(None, description="API calls limit", ge=0)
    portfolio_limit: Optional[int] = Field(None, description="Portfolio limit", ge=0)
    watchlist_limit: Optional[int] = Field(None, description="Watchlist limit", ge=0)
    
    # Features
    features: List[str] = Field(..., description="Plan features")
    
    # Stripe information
    stripe_price_id_monthly: Optional[str] = Field(None, description="Stripe monthly price ID")
    stripe_price_id_yearly: Optional[str] = Field(None, description="Stripe yearly price ID")


# ============================================================================
# NOTIFICATIONS
# ============================================================================

class UserNotificationBase(CapitolScopeBaseModel):
    """Base user notification schema."""
    type: str = Field(..., description="Notification type", max_length=50)
    title: str = Field(..., description="Notification title", max_length=200)
    message: str = Field(..., description="Notification message")
    
    # Notification data
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    
    # Status
    is_read: bool = Field(False, description="Read status")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    
    # Delivery
    delivery_method: str = Field("in_app", description="Delivery method")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    
    # Expiration
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class UserNotificationCreate(UserNotificationBase):
    """Schema for creating user notifications."""
    user_id: uuid.UUID = Field(..., description="User ID")


class UserNotificationUpdate(CapitolScopeBaseModel):
    """Schema for updating user notifications."""
    is_read: Optional[bool] = Field(None, description="Read status")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")


class UserNotificationResponse(UserNotificationBase, IDMixin, TimestampMixin):
    """Schema for user notification responses."""
    user_id: uuid.UUID = Field(..., description="User ID")


# ============================================================================
# USER PREFERENCES
# ============================================================================

class UserPreferencesBase(CapitolScopeBaseModel):
    """Base user preferences schema."""
    # Display preferences
    theme: str = Field("light", description="UI theme (light/dark)")
    language: str = Field("en", description="Language code", max_length=5)
    timezone: str = Field("UTC", description="Timezone", max_length=50)
    
    # Notification preferences
    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences, description="Notification preferences")
    
    # Trading preferences
    default_portfolio: Optional[int] = Field(None, description="Default portfolio ID")
    show_performance: bool = Field(True, description="Show performance metrics")
    show_benchmarks: bool = Field(True, description="Show benchmark comparisons")
    
    # Privacy preferences
    profile_public: bool = Field(True, description="Public profile")
    show_portfolio: bool = Field(False, description="Show portfolio publicly")
    show_watchlist: bool = Field(False, description="Show watchlist publicly")
    
    # Data preferences
    data_retention_days: int = Field(365, description="Data retention days", ge=30, le=3650)
    
    # Metadata
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Custom settings")


class UserPreferencesCreate(UserPreferencesBase):
    """Schema for creating user preferences."""
    user_id: uuid.UUID = Field(..., description="User ID")


class UserPreferencesUpdate(CapitolScopeBaseModel):
    """Schema for updating user preferences."""
    theme: Optional[str] = Field(None, description="UI theme")
    language: Optional[str] = Field(None, description="Language code", max_length=5)
    timezone: Optional[str] = Field(None, description="Timezone", max_length=50)
    notifications: Optional[NotificationPreferences] = Field(None, description="Notification preferences")
    default_portfolio: Optional[int] = Field(None, description="Default portfolio ID")
    show_performance: Optional[bool] = Field(None, description="Show performance metrics")
    show_benchmarks: Optional[bool] = Field(None, description="Show benchmark comparisons")
    profile_public: Optional[bool] = Field(None, description="Public profile")
    show_portfolio: Optional[bool] = Field(None, description="Show portfolio publicly")
    show_watchlist: Optional[bool] = Field(None, description="Show watchlist publicly")
    data_retention_days: Optional[int] = Field(None, description="Data retention days", ge=30, le=3650)
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Custom settings")


class UserPreferencesResponse(UserPreferencesBase, IDMixin, TimestampMixin):
    """Schema for user preferences responses."""
    user_id: uuid.UUID = Field(..., description="User ID")


# ============================================================================
# SEARCH AND FILTER SCHEMAS
# ============================================================================

class UserSearchParams(CapitolScopeBaseModel):
    """User search parameters."""
    query: Optional[str] = Field(None, description="Search query (name, username, email)", max_length=200)
    is_active: Optional[bool] = Field(None, description="Active status filter")
    is_verified: Optional[bool] = Field(None, description="Verification status filter")
    subscription_tier: Optional[SubscriptionTier] = Field(None, description="Subscription tier filter")
    
    # Registration date filters
    registered_after: Optional[datetime] = Field(None, description="Registered after date")
    registered_before: Optional[datetime] = Field(None, description="Registered before date")
    
    # Activity filters
    last_login_after: Optional[datetime] = Field(None, description="Last login after date")
    last_login_before: Optional[datetime] = Field(None, description="Last login before date")
    
    @field_validator('registered_before')
    @classmethod
    def validate_registration_date_range(cls, v, values):
        """Validate registration date range."""
        after_date = values.get('registered_after')
        if after_date and v and v < after_date:
            raise ValueError('Registered before must be after registered after')
        return v
    
    @field_validator('last_login_before')
    @classmethod
    def validate_login_date_range(cls, v, values):
        """Validate login date range."""
        after_date = values.get('last_login_after')
        if after_date and v and v < after_date:
            raise ValueError('Last login before must be after last login after')
        return v


# ============================================================================
# BULK OPERATIONS
# ============================================================================

class BulkUserCreate(CapitolScopeBaseModel):
    """Schema for bulk creating users."""
    users: List[UserCreate] = Field(..., description="List of users to create")
    
    @field_validator('users')
    @classmethod
    def validate_users_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 100:
            raise ValueError('Cannot create more than 100 users at once')
        return v


class BulkUserUpdate(CapitolScopeBaseModel):
    """Schema for bulk updating users."""
    user_ids: List[uuid.UUID] = Field(..., description="List of user IDs to update")
    updates: UserUpdate = Field(..., description="Updates to apply")
    
    @field_validator('user_ids')
    @classmethod
    def validate_user_ids_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 100:
            raise ValueError('Cannot update more than 100 users at once')
        return v


# ============================================================================
# ANALYTICS AND REPORTING
# ============================================================================

class UserAnalytics(CapitolScopeBaseModel):
    """User analytics data."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Activity metrics
    login_count: int = Field(..., description="Total login count", ge=0)
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    avg_session_duration: Optional[float] = Field(None, description="Average session duration in minutes")
    
    # Usage metrics
    api_calls_count: int = Field(..., description="Total API calls", ge=0)
    features_used: List[str] = Field(..., description="Features used")
    
    # Engagement metrics
    portfolios_created: int = Field(..., description="Portfolios created", ge=0)
    watchlists_created: int = Field(..., description="Watchlists created", ge=0)
    notifications_received: int = Field(..., description="Notifications received", ge=0)
    
    # Period information
    period_start: Optional[datetime] = Field(None, description="Analytics period start")
    period_end: Optional[datetime] = Field(None, description="Analytics period end") 