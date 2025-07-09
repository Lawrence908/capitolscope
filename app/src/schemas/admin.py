"""
Admin panel, analytics, and system management Pydantic schemas.

This module contains all schemas related to administrative functions,
system analytics, and management operations for the CapitolScope API.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union

from pydantic import Field, field_validator, HttpUrl

from schemas.base import (
    CapitolScopeBaseModel, IDMixin, UUIDMixin, TimestampMixin,
    PerformanceMetrics
)


# ============================================================================
# SYSTEM MONITORING
# ============================================================================

class SystemMetricsBase(CapitolScopeBaseModel):
    """Base system metrics schema."""
    metric_type: str = Field(..., description="Metric type", max_length=50)
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit", max_length=20)
    
    # Metadata
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    timestamp: datetime = Field(..., description="Metric timestamp")
    
    # Thresholds
    warning_threshold: Optional[float] = Field(None, description="Warning threshold")
    critical_threshold: Optional[float] = Field(None, description="Critical threshold")


class SystemMetricsCreate(SystemMetricsBase):
    """Schema for creating system metrics."""
    pass


class SystemMetricsResponse(SystemMetricsBase, IDMixin, TimestampMixin):
    """Schema for system metrics responses."""
    # Status
    status: str = Field("normal", description="Metric status")
    
    # Trends
    trend_1h: Optional[float] = Field(None, description="1-hour trend")
    trend_24h: Optional[float] = Field(None, description="24-hour trend")
    trend_7d: Optional[float] = Field(None, description="7-day trend")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate metric status."""
        valid_statuses = ['normal', 'warning', 'critical']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class SystemStatusResponse(CapitolScopeBaseModel):
    """System status overview."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Status timestamp")
    
    # Component statuses
    database: Dict[str, Any] = Field(..., description="Database status")
    cache: Dict[str, Any] = Field(..., description="Cache status")
    queue: Dict[str, Any] = Field(..., description="Queue status")
    external_apis: Dict[str, Any] = Field(..., description="External API status")
    
    # Performance metrics
    response_time_ms: float = Field(..., description="Average response time")
    error_rate: float = Field(..., description="Error rate percentage")
    uptime_percentage: float = Field(..., description="Uptime percentage")
    
    # Resource usage
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    
    # Recent incidents
    incidents: Optional[List[Dict[str, Any]]] = Field(None, description="Recent incidents")


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditLogBase(CapitolScopeBaseModel):
    """Base audit log schema."""
    action: str = Field(..., description="Action performed", max_length=100)
    entity_type: str = Field(..., description="Entity type", max_length=50)
    entity_id: Optional[str] = Field(None, description="Entity ID", max_length=100)
    
    # User information
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    user_email: Optional[str] = Field(None, description="User email", max_length=255)
    user_ip: Optional[str] = Field(None, description="User IP address", max_length=45)
    user_agent: Optional[str] = Field(None, description="User agent")
    
    # Context
    request_id: Optional[str] = Field(None, description="Request ID", max_length=100)
    session_id: Optional[str] = Field(None, description="Session ID", max_length=100)
    
    # Details
    old_values: Optional[Dict[str, Any]] = Field(None, description="Old values")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Result
    success: bool = Field(True, description="Action success")
    error_message: Optional[str] = Field(None, description="Error message")


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs."""
    pass


class AuditLogResponse(AuditLogBase, IDMixin, TimestampMixin):
    """Schema for audit log responses."""
    pass


class AuditLogSearchParams(CapitolScopeBaseModel):
    """Audit log search parameters."""
    query: Optional[str] = Field(None, description="Search query", max_length=200)
    action: Optional[str] = Field(None, description="Action filter", max_length=100)
    entity_type: Optional[str] = Field(None, description="Entity type filter", max_length=50)
    entity_id: Optional[str] = Field(None, description="Entity ID filter", max_length=100)
    user_id: Optional[uuid.UUID] = Field(None, description="User ID filter")
    user_email: Optional[str] = Field(None, description="User email filter", max_length=255)
    
    # Date filters
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    
    # Status filters
    success: Optional[bool] = Field(None, description="Success filter")
    
    @field_validator('created_before')
    @classmethod
    def validate_date_range(cls, v, values):
        """Validate date range."""
        after_date = values.get('created_after')
        if after_date and v and v < after_date:
            raise ValueError('Created before must be after created after')
        return v


# ============================================================================
# ANALYTICS DASHBOARD
# ============================================================================

class DashboardMetrics(CapitolScopeBaseModel):
    """Dashboard metrics overview."""
    period: str = Field(..., description="Metrics period (1h, 24h, 7d, 30d)")
    
    # User metrics
    total_users: int = Field(..., description="Total users", ge=0)
    active_users: int = Field(..., description="Active users", ge=0)
    new_users: int = Field(..., description="New users", ge=0)
    
    # Trading metrics
    total_trades: int = Field(..., description="Total trades", ge=0)
    trade_volume: int = Field(..., description="Trade volume in cents", ge=0)
    unique_members: int = Field(..., description="Unique members trading", ge=0)
    
    # Platform metrics
    api_calls: int = Field(..., description="API calls", ge=0)
    error_rate: float = Field(..., description="Error rate percentage", ge=0, le=100)
    avg_response_time: float = Field(..., description="Average response time in ms", ge=0)
    
    # Engagement metrics
    social_posts: int = Field(..., description="Social posts", ge=0)
    community_posts: int = Field(..., description="Community posts", ge=0)
    notifications_sent: int = Field(..., description="Notifications sent", ge=0)
    
    # Financial metrics
    subscription_revenue: int = Field(..., description="Subscription revenue in cents", ge=0)
    api_revenue: int = Field(..., description="API revenue in cents", ge=0)
    
    # Calculated at
    calculated_at: datetime = Field(..., description="Metrics calculation timestamp")


class UserActivityMetrics(CapitolScopeBaseModel):
    """User activity metrics."""
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Activity counts
    logins: int = Field(..., description="Login count", ge=0)
    api_calls: int = Field(..., description="API calls", ge=0)
    pages_viewed: int = Field(..., description="Pages viewed", ge=0)
    
    # Feature usage
    features_used: List[str] = Field(..., description="Features used")
    most_used_feature: Optional[str] = Field(None, description="Most used feature")
    
    # Engagement
    session_duration: float = Field(..., description="Average session duration in minutes", ge=0)
    bounce_rate: float = Field(..., description="Bounce rate percentage", ge=0, le=100)
    
    # Social activity
    posts_created: int = Field(..., description="Posts created", ge=0)
    comments_made: int = Field(..., description="Comments made", ge=0)
    
    # Period information
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")


class ContentModerationMetrics(CapitolScopeBaseModel):
    """Content moderation metrics."""
    # Content counts
    total_posts: int = Field(..., description="Total posts", ge=0)
    total_comments: int = Field(..., description="Total comments", ge=0)
    
    # Moderation actions
    posts_flagged: int = Field(..., description="Posts flagged", ge=0)
    posts_removed: int = Field(..., description="Posts removed", ge=0)
    comments_flagged: int = Field(..., description="Comments flagged", ge=0)
    comments_removed: int = Field(..., description="Comments removed", ge=0)
    
    # User actions
    users_warned: int = Field(..., description="Users warned", ge=0)
    users_suspended: int = Field(..., description="Users suspended", ge=0)
    users_banned: int = Field(..., description="Users banned", ge=0)
    
    # Moderation queue
    pending_reviews: int = Field(..., description="Pending reviews", ge=0)
    avg_review_time: float = Field(..., description="Average review time in minutes", ge=0)
    
    # Period information
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")


# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

class ConfigurationBase(CapitolScopeBaseModel):
    """Base configuration schema."""
    key: str = Field(..., description="Configuration key", max_length=100)
    value: str = Field(..., description="Configuration value", max_length=1000)
    
    # Metadata
    category: str = Field(..., description="Configuration category", max_length=50)
    description: Optional[str] = Field(None, description="Configuration description")
    
    # Validation
    data_type: str = Field("string", description="Data type")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    
    # Settings
    is_sensitive: bool = Field(False, description="Contains sensitive data")
    is_required: bool = Field(False, description="Required configuration")
    
    @field_validator('data_type')
    @classmethod
    def validate_data_type(cls, v):
        """Validate data type."""
        valid_types = ['string', 'integer', 'float', 'boolean', 'json', 'url']
        if v not in valid_types:
            raise ValueError(f'Data type must be one of: {valid_types}')
        return v


class ConfigurationCreate(ConfigurationBase):
    """Schema for creating configurations."""
    pass


class ConfigurationUpdate(CapitolScopeBaseModel):
    """Schema for updating configurations."""
    value: Optional[str] = Field(None, description="Configuration value", max_length=1000)
    description: Optional[str] = Field(None, description="Configuration description")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    is_sensitive: Optional[bool] = Field(None, description="Contains sensitive data")
    is_required: Optional[bool] = Field(None, description="Required configuration")


class ConfigurationResponse(ConfigurationBase, IDMixin, TimestampMixin):
    """Schema for configuration responses."""
    # Hide sensitive values
    @field_validator('value')
    @classmethod
    def hide_sensitive_value(cls, v, values):
        """Hide sensitive configuration values."""
        if values.get('is_sensitive'):
            return '***HIDDEN***'
        return v


# ============================================================================
# FEATURE FLAGS
# ============================================================================

class FeatureFlagBase(CapitolScopeBaseModel):
    """Base feature flag schema."""
    key: str = Field(..., description="Feature flag key", max_length=100)
    name: str = Field(..., description="Feature flag name", max_length=200)
    description: Optional[str] = Field(None, description="Feature flag description")
    
    # Flag settings
    is_enabled: bool = Field(False, description="Flag enabled status")
    rollout_percentage: float = Field(0.0, description="Rollout percentage", ge=0, le=100)
    
    # Targeting
    user_groups: Optional[List[str]] = Field(None, description="Target user groups")
    subscription_tiers: Optional[List[str]] = Field(None, description="Target subscription tiers")
    
    # Conditions
    conditions: Optional[Dict[str, Any]] = Field(None, description="Flag conditions")
    
    # Metadata
    category: str = Field("general", description="Feature category", max_length=50)
    tags: Optional[List[str]] = Field(None, description="Feature tags")
    
    # Lifecycle
    start_date: Optional[datetime] = Field(None, description="Flag start date")
    end_date: Optional[datetime] = Field(None, description="Flag end date")


class FeatureFlagCreate(FeatureFlagBase):
    """Schema for creating feature flags."""
    pass


class FeatureFlagUpdate(CapitolScopeBaseModel):
    """Schema for updating feature flags."""
    name: Optional[str] = Field(None, description="Feature flag name", max_length=200)
    description: Optional[str] = Field(None, description="Feature flag description")
    is_enabled: Optional[bool] = Field(None, description="Flag enabled status")
    rollout_percentage: Optional[float] = Field(None, description="Rollout percentage", ge=0, le=100)
    user_groups: Optional[List[str]] = Field(None, description="Target user groups")
    subscription_tiers: Optional[List[str]] = Field(None, description="Target subscription tiers")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Flag conditions")
    category: Optional[str] = Field(None, description="Feature category", max_length=50)
    tags: Optional[List[str]] = Field(None, description="Feature tags")
    start_date: Optional[datetime] = Field(None, description="Flag start date")
    end_date: Optional[datetime] = Field(None, description="Flag end date")


class FeatureFlagResponse(FeatureFlagBase, IDMixin, TimestampMixin):
    """Schema for feature flag responses."""
    # Usage statistics
    usage_count: int = Field(0, description="Usage count", ge=0)
    unique_users: int = Field(0, description="Unique users", ge=0)
    
    # Status
    is_active: bool = Field(False, description="Currently active")
    last_used: Optional[datetime] = Field(None, description="Last used timestamp")


# ============================================================================
# DATA MANAGEMENT
# ============================================================================

class DataExportRequest(CapitolScopeBaseModel):
    """Data export request schema."""
    export_type: str = Field(..., description="Export type")
    format: str = Field("json", description="Export format")
    
    # Filters
    filters: Optional[Dict[str, Any]] = Field(None, description="Export filters")
    date_range: Optional[Dict[str, Any]] = Field(None, description="Date range filter")
    
    # Options
    include_metadata: bool = Field(True, description="Include metadata")
    compress: bool = Field(False, description="Compress export")
    
    # Delivery
    delivery_method: str = Field("download", description="Delivery method")
    email_notification: bool = Field(True, description="Email notification")
    
    @field_validator('export_type')
    @classmethod
    def validate_export_type(cls, v):
        """Validate export type."""
        valid_types = ['users', 'trades', 'members', 'securities', 'posts', 'analytics']
        if v not in valid_types:
            raise ValueError(f'Export type must be one of: {valid_types}')
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate export format."""
        valid_formats = ['json', 'csv', 'excel', 'parquet']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v
    
    @field_validator('delivery_method')
    @classmethod
    def validate_delivery_method(cls, v):
        """Validate delivery method."""
        valid_methods = ['download', 'email', 's3', 'api']
        if v not in valid_methods:
            raise ValueError(f'Delivery method must be one of: {valid_methods}')
        return v


class DataExportResponse(CapitolScopeBaseModel):
    """Data export response schema."""
    export_id: str = Field(..., description="Export ID")
    status: str = Field(..., description="Export status")
    
    # Progress
    progress_percentage: float = Field(0.0, description="Progress percentage", ge=0, le=100)
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion")
    
    # Results
    download_url: Optional[HttpUrl] = Field(None, description="Download URL")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    record_count: Optional[int] = Field(None, description="Record count", ge=0)
    
    # Metadata
    created_at: datetime = Field(..., description="Export creation time")
    completed_at: Optional[datetime] = Field(None, description="Export completion time")
    expires_at: Optional[datetime] = Field(None, description="Download expiration time")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate export status."""
        valid_statuses = ['queued', 'processing', 'completed', 'failed', 'expired']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class DataImportRequest(CapitolScopeBaseModel):
    """Data import request schema."""
    import_type: str = Field(..., description="Import type")
    format: str = Field("json", description="Import format")
    
    # Data source
    source_url: Optional[HttpUrl] = Field(None, description="Source URL")
    file_content: Optional[str] = Field(None, description="File content")
    
    # Options
    validate_data: bool = Field(True, description="Validate data")
    skip_duplicates: bool = Field(True, description="Skip duplicates")
    update_existing: bool = Field(False, description="Update existing records")
    
    # Mapping
    field_mapping: Optional[Dict[str, str]] = Field(None, description="Field mapping")
    
    @field_validator('import_type')
    @classmethod
    def validate_import_type(cls, v):
        """Validate import type."""
        valid_types = ['users', 'trades', 'members', 'securities', 'posts']
        if v not in valid_types:
            raise ValueError(f'Import type must be one of: {valid_types}')
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate import format."""
        valid_formats = ['json', 'csv', 'excel']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v


class DataImportResponse(CapitolScopeBaseModel):
    """Data import response schema."""
    import_id: str = Field(..., description="Import ID")
    status: str = Field(..., description="Import status")
    
    # Progress
    progress_percentage: float = Field(0.0, description="Progress percentage", ge=0, le=100)
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion")
    
    # Results
    total_records: Optional[int] = Field(None, description="Total records", ge=0)
    successful_records: Optional[int] = Field(None, description="Successful records", ge=0)
    failed_records: Optional[int] = Field(None, description="Failed records", ge=0)
    skipped_records: Optional[int] = Field(None, description="Skipped records", ge=0)
    
    # Errors
    errors: Optional[List[str]] = Field(None, description="Error messages")
    
    # Metadata
    created_at: datetime = Field(..., description="Import creation time")
    completed_at: Optional[datetime] = Field(None, description="Import completion time")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate import status."""
        valid_statuses = ['queued', 'processing', 'completed', 'failed', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


# ============================================================================
# MACHINE LEARNING MANAGEMENT
# ============================================================================

class MLModelBase(CapitolScopeBaseModel):
    """Base ML model schema."""
    name: str = Field(..., description="Model name", max_length=100)
    description: Optional[str] = Field(None, description="Model description")
    
    # Model information
    model_type: str = Field(..., description="Model type", max_length=50)
    version: str = Field(..., description="Model version", max_length=20)
    
    # Training information
    training_data_size: Optional[int] = Field(None, description="Training data size", ge=0)
    training_duration: Optional[float] = Field(None, description="Training duration in hours", ge=0)
    
    # Performance metrics
    accuracy: Optional[float] = Field(None, description="Model accuracy", ge=0, le=1)
    precision: Optional[float] = Field(None, description="Model precision", ge=0, le=1)
    recall: Optional[float] = Field(None, description="Model recall", ge=0, le=1)
    f1_score: Optional[float] = Field(None, description="F1 score", ge=0, le=1)
    
    # Deployment information
    is_deployed: bool = Field(False, description="Deployment status")
    deployment_url: Optional[HttpUrl] = Field(None, description="Deployment URL")
    
    # Configuration
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Model hyperparameters")
    features: Optional[List[str]] = Field(None, description="Model features")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MLModelCreate(MLModelBase):
    """Schema for creating ML models."""
    pass


class MLModelUpdate(CapitolScopeBaseModel):
    """Schema for updating ML models."""
    name: Optional[str] = Field(None, description="Model name", max_length=100)
    description: Optional[str] = Field(None, description="Model description")
    version: Optional[str] = Field(None, description="Model version", max_length=20)
    training_data_size: Optional[int] = Field(None, description="Training data size", ge=0)
    training_duration: Optional[float] = Field(None, description="Training duration in hours", ge=0)
    accuracy: Optional[float] = Field(None, description="Model accuracy", ge=0, le=1)
    precision: Optional[float] = Field(None, description="Model precision", ge=0, le=1)
    recall: Optional[float] = Field(None, description="Model recall", ge=0, le=1)
    f1_score: Optional[float] = Field(None, description="F1 score", ge=0, le=1)
    is_deployed: Optional[bool] = Field(None, description="Deployment status")
    deployment_url: Optional[HttpUrl] = Field(None, description="Deployment URL")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Model hyperparameters")
    features: Optional[List[str]] = Field(None, description="Model features")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MLModelResponse(MLModelBase, IDMixin, TimestampMixin):
    """Schema for ML model responses."""
    # Usage statistics
    prediction_count: int = Field(0, description="Prediction count", ge=0)
    last_prediction: Optional[datetime] = Field(None, description="Last prediction timestamp")
    
    # Health monitoring
    health_score: Optional[float] = Field(None, description="Model health score", ge=0, le=1)
    drift_score: Optional[float] = Field(None, description="Data drift score", ge=0, le=1)
    
    # Performance monitoring
    recent_accuracy: Optional[float] = Field(None, description="Recent accuracy", ge=0, le=1)
    performance_trend: Optional[str] = Field(None, description="Performance trend")


class MLPredictionBase(CapitolScopeBaseModel):
    """Base ML prediction schema."""
    model_id: int = Field(..., description="Model ID")
    
    # Input data
    input_data: Dict[str, Any] = Field(..., description="Input data")
    
    # Prediction results
    prediction: Union[float, int, str, Dict[str, Any]] = Field(..., description="Prediction result")
    confidence: Optional[float] = Field(None, description="Prediction confidence", ge=0, le=1)
    
    # Metadata
    prediction_time: float = Field(..., description="Prediction time in milliseconds", ge=0)
    model_version: str = Field(..., description="Model version used")
    
    # Context
    context: Optional[Dict[str, Any]] = Field(None, description="Prediction context")


class MLPredictionCreate(MLPredictionBase):
    """Schema for creating ML predictions."""
    pass


class MLPredictionResponse(MLPredictionBase, IDMixin, TimestampMixin):
    """Schema for ML prediction responses."""
    # Validation
    is_validated: bool = Field(False, description="Prediction validated")
    actual_value: Optional[Union[float, int, str]] = Field(None, description="Actual value")
    validation_score: Optional[float] = Field(None, description="Validation score")
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message")
    
    # Usage tracking
    feedback_score: Optional[float] = Field(None, description="User feedback score", ge=0, le=1)
    feedback_comment: Optional[str] = Field(None, description="User feedback comment") 