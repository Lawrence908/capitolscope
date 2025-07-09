"""
Social media integration and community features Pydantic schemas.

This module contains all schemas related to social media posting,
community interactions, and social trading features.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import Field, field_validator, HttpUrl

from schemas.base import (
    CapitolScopeBaseModel, IDMixin, UUIDMixin, TimestampMixin,
    SocialPlatform
)


# ============================================================================
# SOCIAL MEDIA POSTS
# ============================================================================

class SocialPostBase(CapitolScopeBaseModel):
    """Base social media post schema."""
    platform: SocialPlatform = Field(..., description="Social media platform")
    content: str = Field(..., description="Post content", max_length=2000)
    
    # Post metadata
    post_type: str = Field("trade_alert", description="Type of post")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled post time")
    
    # Trade-related data
    trade_id: Optional[int] = Field(None, description="Related trade ID")
    member_id: Optional[int] = Field(None, description="Related member ID")
    
    # Template and formatting
    template_id: Optional[int] = Field(None, description="Template used")
    hashtags: Optional[List[str]] = Field(None, description="Hashtags to include")
    mentions: Optional[List[str]] = Field(None, description="Users to mention")
    
    # Media attachments
    image_url: Optional[HttpUrl] = Field(None, description="Attached image URL")
    chart_config: Optional[Dict[str, Any]] = Field(None, description="Chart configuration")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        """Validate social platform."""
        valid_platforms = ['twitter', 'linkedin', 'discord', 'telegram', 'reddit', 'facebook']
        if v not in valid_platforms:
            raise ValueError(f'Platform must be one of: {valid_platforms}')
        return v
    
    @field_validator('post_type')
    @classmethod
    def validate_post_type(cls, v):
        """Validate post type."""
        valid_types = ['trade_alert', 'market_update', 'portfolio_update', 'educational', 'custom']
        if v not in valid_types:
            raise ValueError(f'Post type must be one of: {valid_types}')
        return v


class SocialPostCreate(SocialPostBase):
    """Schema for creating social media posts."""
    user_id: uuid.UUID = Field(..., description="User ID")


class SocialPostUpdate(CapitolScopeBaseModel):
    """Schema for updating social media posts."""
    content: Optional[str] = Field(None, description="Post content", max_length=2000)
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled post time")
    hashtags: Optional[List[str]] = Field(None, description="Hashtags to include")
    mentions: Optional[List[str]] = Field(None, description="Users to mention")
    image_url: Optional[HttpUrl] = Field(None, description="Attached image URL")
    chart_config: Optional[Dict[str, Any]] = Field(None, description="Chart configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SocialPostResponse(SocialPostBase, IDMixin, TimestampMixin):
    """Schema for social media post responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Post status
    status: str = Field("draft", description="Post status")
    posted_at: Optional[datetime] = Field(None, description="Actual post time")
    
    # Platform response
    platform_post_id: Optional[str] = Field(None, description="Platform post ID")
    platform_url: Optional[HttpUrl] = Field(None, description="Platform post URL")
    
    # Engagement metrics
    likes: Optional[int] = Field(None, description="Number of likes", ge=0)
    shares: Optional[int] = Field(None, description="Number of shares", ge=0)
    comments: Optional[int] = Field(None, description="Number of comments", ge=0)
    engagement_rate: Optional[float] = Field(None, description="Engagement rate")
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts", ge=0)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate post status."""
        valid_statuses = ['draft', 'scheduled', 'posting', 'posted', 'failed', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


# ============================================================================
# POST TEMPLATES
# ============================================================================

class PostTemplateBase(CapitolScopeBaseModel):
    """Base post template schema."""
    name: str = Field(..., description="Template name", max_length=100)
    description: Optional[str] = Field(None, description="Template description")
    
    # Template content
    content_template: str = Field(..., description="Template content with placeholders")
    
    # Platform settings
    platforms: List[SocialPlatform] = Field(..., description="Supported platforms")
    
    # Template configuration
    variables: Optional[Dict[str, str]] = Field(None, description="Template variables")
    default_hashtags: Optional[List[str]] = Field(None, description="Default hashtags")
    
    # Categorization
    category: str = Field("general", description="Template category")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    
    # Settings
    is_active: bool = Field(True, description="Template active status")
    is_public: bool = Field(False, description="Public template")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate template category."""
        valid_categories = ['general', 'trade_alert', 'market_update', 'portfolio', 'educational']
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {valid_categories}')
        return v


class PostTemplateCreate(PostTemplateBase):
    """Schema for creating post templates."""
    user_id: uuid.UUID = Field(..., description="User ID")


class PostTemplateUpdate(CapitolScopeBaseModel):
    """Schema for updating post templates."""
    name: Optional[str] = Field(None, description="Template name", max_length=100)
    description: Optional[str] = Field(None, description="Template description")
    content_template: Optional[str] = Field(None, description="Template content")
    platforms: Optional[List[SocialPlatform]] = Field(None, description="Supported platforms")
    variables: Optional[Dict[str, str]] = Field(None, description="Template variables")
    default_hashtags: Optional[List[str]] = Field(None, description="Default hashtags")
    category: Optional[str] = Field(None, description="Template category")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    is_active: Optional[bool] = Field(None, description="Template active status")
    is_public: Optional[bool] = Field(None, description="Public template")


class PostTemplateResponse(PostTemplateBase, IDMixin, TimestampMixin):
    """Schema for post template responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times used", ge=0)
    last_used: Optional[datetime] = Field(None, description="Last used timestamp")
    
    # User info (for public templates)
    user_name: Optional[str] = Field(None, description="Template author name")


# ============================================================================
# SOCIAL AUTOMATION
# ============================================================================

class AutomationRuleBase(CapitolScopeBaseModel):
    """Base automation rule schema."""
    name: str = Field(..., description="Rule name", max_length=100)
    description: Optional[str] = Field(None, description="Rule description")
    
    # Rule configuration
    trigger_type: str = Field(..., description="Trigger type")
    trigger_config: Dict[str, Any] = Field(..., description="Trigger configuration")
    
    # Actions
    action_type: str = Field("social_post", description="Action type")
    action_config: Dict[str, Any] = Field(..., description="Action configuration")
    
    # Conditions
    conditions: Optional[List[Dict[str, Any]]] = Field(None, description="Rule conditions")
    
    # Settings
    is_active: bool = Field(True, description="Rule active status")
    priority: int = Field(1, description="Rule priority", ge=1, le=10)
    
    # Rate limiting
    max_posts_per_hour: Optional[int] = Field(None, description="Max posts per hour", ge=1)
    max_posts_per_day: Optional[int] = Field(None, description="Max posts per day", ge=1)
    
    @field_validator('trigger_type')
    @classmethod
    def validate_trigger_type(cls, v):
        """Validate trigger type."""
        valid_triggers = ['trade_alert', 'price_change', 'portfolio_update', 'schedule', 'manual']
        if v not in valid_triggers:
            raise ValueError(f'Trigger type must be one of: {valid_triggers}')
        return v
    
    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v):
        """Validate action type."""
        valid_actions = ['social_post', 'notification', 'email', 'webhook']
        if v not in valid_actions:
            raise ValueError(f'Action type must be one of: {valid_actions}')
        return v


class AutomationRuleCreate(AutomationRuleBase):
    """Schema for creating automation rules."""
    user_id: uuid.UUID = Field(..., description="User ID")


class AutomationRuleUpdate(CapitolScopeBaseModel):
    """Schema for updating automation rules."""
    name: Optional[str] = Field(None, description="Rule name", max_length=100)
    description: Optional[str] = Field(None, description="Rule description")
    trigger_config: Optional[Dict[str, Any]] = Field(None, description="Trigger configuration")
    action_config: Optional[Dict[str, Any]] = Field(None, description="Action configuration")
    conditions: Optional[List[Dict[str, Any]]] = Field(None, description="Rule conditions")
    is_active: Optional[bool] = Field(None, description="Rule active status")
    priority: Optional[int] = Field(None, description="Rule priority", ge=1, le=10)
    max_posts_per_hour: Optional[int] = Field(None, description="Max posts per hour", ge=1)
    max_posts_per_day: Optional[int] = Field(None, description="Max posts per day", ge=1)


class AutomationRuleResponse(AutomationRuleBase, IDMixin, TimestampMixin):
    """Schema for automation rule responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Execution statistics
    execution_count: int = Field(0, description="Number of executions", ge=0)
    last_executed: Optional[datetime] = Field(None, description="Last execution timestamp")
    success_count: int = Field(0, description="Successful executions", ge=0)
    error_count: int = Field(0, description="Failed executions", ge=0)
    
    # Current state
    last_error: Optional[str] = Field(None, description="Last error message")
    next_execution: Optional[datetime] = Field(None, description="Next scheduled execution")


# ============================================================================
# ENGAGEMENT TRACKING
# ============================================================================

class EngagementMetricBase(CapitolScopeBaseModel):
    """Base engagement metric schema."""
    post_id: int = Field(..., description="Social post ID")
    platform: SocialPlatform = Field(..., description="Social platform")
    
    # Engagement data
    likes: int = Field(0, description="Number of likes", ge=0)
    shares: int = Field(0, description="Number of shares", ge=0)
    comments: int = Field(0, description="Number of comments", ge=0)
    views: Optional[int] = Field(None, description="Number of views", ge=0)
    clicks: Optional[int] = Field(None, description="Number of clicks", ge=0)
    
    # Calculated metrics
    engagement_rate: Optional[float] = Field(None, description="Engagement rate")
    reach: Optional[int] = Field(None, description="Post reach", ge=0)
    impressions: Optional[int] = Field(None, description="Post impressions", ge=0)
    
    # Timestamp
    measured_at: datetime = Field(..., description="Measurement timestamp")


class EngagementMetricCreate(EngagementMetricBase):
    """Schema for creating engagement metrics."""
    pass


class EngagementMetricResponse(EngagementMetricBase, IDMixin, TimestampMixin):
    """Schema for engagement metric responses."""
    pass


# ============================================================================
# COMMUNITY FEATURES
# ============================================================================

class CommunityPostBase(CapitolScopeBaseModel):
    """Base community post schema."""
    title: str = Field(..., description="Post title", max_length=200)
    content: str = Field(..., description="Post content", max_length=10000)
    
    # Post type and category
    post_type: str = Field("discussion", description="Post type")
    category: str = Field("general", description="Post category")
    
    # Related data
    trade_id: Optional[int] = Field(None, description="Related trade ID")
    member_id: Optional[int] = Field(None, description="Related member ID")
    security_id: Optional[int] = Field(None, description="Related security ID")
    
    # Tagging
    tags: Optional[List[str]] = Field(None, description="Post tags")
    
    # Settings
    is_pinned: bool = Field(False, description="Pinned post")
    is_locked: bool = Field(False, description="Locked post")
    allow_comments: bool = Field(True, description="Allow comments")
    
    @field_validator('post_type')
    @classmethod
    def validate_post_type(cls, v):
        """Validate post type."""
        valid_types = ['discussion', 'analysis', 'question', 'news', 'educational']
        if v not in valid_types:
            raise ValueError(f'Post type must be one of: {valid_types}')
        return v
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate post category."""
        valid_categories = ['general', 'trading', 'politics', 'analysis', 'education']
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {valid_categories}')
        return v


class CommunityPostCreate(CommunityPostBase):
    """Schema for creating community posts."""
    user_id: uuid.UUID = Field(..., description="User ID")


class CommunityPostUpdate(CapitolScopeBaseModel):
    """Schema for updating community posts."""
    title: Optional[str] = Field(None, description="Post title", max_length=200)
    content: Optional[str] = Field(None, description="Post content", max_length=10000)
    category: Optional[str] = Field(None, description="Post category")
    tags: Optional[List[str]] = Field(None, description="Post tags")
    is_pinned: Optional[bool] = Field(None, description="Pinned post")
    is_locked: Optional[bool] = Field(None, description="Locked post")
    allow_comments: Optional[bool] = Field(None, description="Allow comments")


class CommunityPostResponse(CommunityPostBase, IDMixin, TimestampMixin):
    """Schema for community post responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Author info
    author_name: Optional[str] = Field(None, description="Author name")
    author_avatar: Optional[HttpUrl] = Field(None, description="Author avatar URL")
    
    # Engagement metrics
    view_count: int = Field(0, description="View count", ge=0)
    like_count: int = Field(0, description="Like count", ge=0)
    comment_count: int = Field(0, description="Comment count", ge=0)
    
    # User interaction
    user_liked: Optional[bool] = Field(None, description="Current user liked")
    user_bookmarked: Optional[bool] = Field(None, description="Current user bookmarked")
    
    # Moderation
    is_reported: bool = Field(False, description="Post has been reported")
    moderation_status: str = Field("approved", description="Moderation status")


class CommunityCommentBase(CapitolScopeBaseModel):
    """Base community comment schema."""
    post_id: int = Field(..., description="Community post ID")
    content: str = Field(..., description="Comment content", max_length=2000)
    
    # Threading
    parent_comment_id: Optional[int] = Field(None, description="Parent comment ID")
    
    # Settings
    is_edited: bool = Field(False, description="Comment edited")
    edited_at: Optional[datetime] = Field(None, description="Edit timestamp")


class CommunityCommentCreate(CommunityCommentBase):
    """Schema for creating community comments."""
    user_id: uuid.UUID = Field(..., description="User ID")


class CommunityCommentUpdate(CapitolScopeBaseModel):
    """Schema for updating community comments."""
    content: Optional[str] = Field(None, description="Comment content", max_length=2000)


class CommunityCommentResponse(CommunityCommentBase, IDMixin, TimestampMixin):
    """Schema for community comment responses."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Author info
    author_name: Optional[str] = Field(None, description="Author name")
    author_avatar: Optional[HttpUrl] = Field(None, description="Author avatar URL")
    
    # Engagement
    like_count: int = Field(0, description="Like count", ge=0)
    
    # User interaction
    user_liked: Optional[bool] = Field(None, description="Current user liked")
    
    # Threading
    reply_count: int = Field(0, description="Reply count", ge=0)
    
    # Moderation
    is_reported: bool = Field(False, description="Comment has been reported")
    moderation_status: str = Field("approved", description="Moderation status")


# ============================================================================
# SEARCH AND FILTER SCHEMAS
# ============================================================================

class SocialPostSearchParams(CapitolScopeBaseModel):
    """Social post search parameters."""
    query: Optional[str] = Field(None, description="Search query", max_length=200)
    user_id: Optional[uuid.UUID] = Field(None, description="User ID filter")
    platform: Optional[SocialPlatform] = Field(None, description="Platform filter")
    post_type: Optional[str] = Field(None, description="Post type filter")
    status: Optional[str] = Field(None, description="Status filter")
    
    # Date filters
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    posted_after: Optional[datetime] = Field(None, description="Posted after date")
    posted_before: Optional[datetime] = Field(None, description="Posted before date")
    
    # Engagement filters
    min_engagement: Optional[float] = Field(None, description="Minimum engagement rate")
    max_engagement: Optional[float] = Field(None, description="Maximum engagement rate")
    
    # Related data filters
    trade_id: Optional[int] = Field(None, description="Trade ID filter")
    member_id: Optional[int] = Field(None, description="Member ID filter")


class CommunityPostSearchParams(CapitolScopeBaseModel):
    """Community post search parameters."""
    query: Optional[str] = Field(None, description="Search query", max_length=200)
    user_id: Optional[uuid.UUID] = Field(None, description="User ID filter")
    post_type: Optional[str] = Field(None, description="Post type filter")
    category: Optional[str] = Field(None, description="Category filter")
    tags: Optional[List[str]] = Field(None, description="Tags filter")
    
    # Date filters
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    
    # Engagement filters
    min_likes: Optional[int] = Field(None, description="Minimum likes", ge=0)
    max_likes: Optional[int] = Field(None, description="Maximum likes", ge=0)
    min_comments: Optional[int] = Field(None, description="Minimum comments", ge=0)
    max_comments: Optional[int] = Field(None, description="Maximum comments", ge=0)
    
    # Status filters
    is_pinned: Optional[bool] = Field(None, description="Pinned filter")
    is_locked: Optional[bool] = Field(None, description="Locked filter")
    moderation_status: Optional[str] = Field(None, description="Moderation status filter")
    
    # Related data filters
    trade_id: Optional[int] = Field(None, description="Trade ID filter")
    member_id: Optional[int] = Field(None, description="Member ID filter")
    security_id: Optional[int] = Field(None, description="Security ID filter")


# ============================================================================
# ANALYTICS AND REPORTING
# ============================================================================

class SocialAnalytics(CapitolScopeBaseModel):
    """Social media analytics data."""
    user_id: uuid.UUID = Field(..., description="User ID")
    platform: Optional[SocialPlatform] = Field(None, description="Platform filter")
    
    # Post metrics
    total_posts: int = Field(..., description="Total posts", ge=0)
    successful_posts: int = Field(..., description="Successful posts", ge=0)
    failed_posts: int = Field(..., description="Failed posts", ge=0)
    
    # Engagement metrics
    total_likes: int = Field(..., description="Total likes", ge=0)
    total_shares: int = Field(..., description="Total shares", ge=0)
    total_comments: int = Field(..., description="Total comments", ge=0)
    avg_engagement_rate: Optional[float] = Field(None, description="Average engagement rate")
    
    # Performance metrics
    best_performing_post: Optional[int] = Field(None, description="Best performing post ID")
    best_engagement_rate: Optional[float] = Field(None, description="Best engagement rate")
    
    # Growth metrics
    followers_gained: Optional[int] = Field(None, description="Followers gained")
    reach_increase: Optional[float] = Field(None, description="Reach increase percentage")
    
    # Period information
    period_start: Optional[datetime] = Field(None, description="Analytics period start")
    period_end: Optional[datetime] = Field(None, description="Analytics period end")


class CommunityAnalytics(CapitolScopeBaseModel):
    """Community analytics data."""
    user_id: Optional[uuid.UUID] = Field(None, description="User ID filter")
    
    # Post metrics
    total_posts: int = Field(..., description="Total posts", ge=0)
    total_comments: int = Field(..., description="Total comments", ge=0)
    total_likes: int = Field(..., description="Total likes", ge=0)
    
    # Activity metrics
    active_users: int = Field(..., description="Active users", ge=0)
    posts_per_day: Optional[float] = Field(None, description="Average posts per day")
    comments_per_post: Optional[float] = Field(None, description="Average comments per post")
    
    # Popular content
    top_posts: Optional[List[int]] = Field(None, description="Top post IDs")
    trending_tags: Optional[List[str]] = Field(None, description="Trending tags")
    
    # Growth metrics
    new_users: Optional[int] = Field(None, description="New users", ge=0)
    retention_rate: Optional[float] = Field(None, description="User retention rate")
    
    # Period information
    period_start: Optional[datetime] = Field(None, description="Analytics period start")
    period_end: Optional[datetime] = Field(None, description="Analytics period end") 