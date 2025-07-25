# Schemas package initialization - API validation and serialization models

# Base schemas and common utilities
from .base import (
    CapitolScopeBaseModel,
    UUIDMixin,
    TimestampMixin,
    
    # Enums
    PoliticalParty,
    Chamber,
    TransactionType,
    SubscriptionTier,
    SubscriptionStatus,
    SocialPlatform,
    
    # Common patterns
    PaginationParams,
    SortParams,
    PaginatedResponse,
    APIResponse,
    ErrorResponse,
    
    # Financial types
    AmountRange,
    PerformanceMetrics,
    TechnicalIndicators,
    
    # Filter types
    DateRangeFilter,
    AmountFilter,
    SearchParams,
    
    # Metadata types
    SocialMediaLinks,
    ResearchLinks,
    NotificationPreferences,
    
    # Health check
    HealthCheckResponse,
    DetailedHealthCheckResponse,
    
    # Validators
    validate_ticker_symbol,
    validate_political_party,
    validate_chamber,
    validate_transaction_type,
)

# Securities schemas
from .securities import (
    # Asset Types
    AssetTypeBase,
    AssetTypeCreate,
    AssetTypeUpdate,
    AssetTypeResponse,
    
    # Sectors
    SectorBase,
    SectorCreate,
    SectorUpdate,
    SectorResponse,
    
    # Exchanges
    ExchangeBase,
    ExchangeCreate,
    ExchangeUpdate,
    ExchangeResponse,
    
    # Securities
    SecurityBase,
    SecurityCreate,
    SecurityUpdate,
    SecurityResponse,
    SecuritySummary,
    
    # Price Data
    DailyPriceBase,
    DailyPriceCreate,
    DailyPriceResponse,
    PriceHistory,
    
    # Corporate Actions
    CorporateActionBase,
    CorporateActionCreate,
    CorporateActionUpdate,
    CorporateActionResponse,
    
    # Search and Filters
    SecuritySearchParams,
    PriceSearchParams,
    
    # Bulk Operations
    BulkSecurityCreate,
    BulkPriceCreate,
    BulkOperationResponse,
)

# Congressional schemas
from .congressional import (
    # Congress Members
    CongressMemberBase,
    CongressMemberCreate,
    CongressMemberUpdate,
    CongressMemberResponse,
    CongressMemberSummary,
    
    # Congressional Trades
    CongressionalTradeBase,
    CongressionalTradeCreate,
    CongressionalTradeUpdate,
    CongressionalTradeResponse,
    CongressionalTradeSummary,
    
    # Search and Filters
    CongressMemberSearchParams,
    CongressionalTradeSearchParams,
    
    # Bulk Operations
    BulkCongressMemberCreate,
    BulkCongressionalTradeCreate,
    
    # Analytics
    MemberTradingStats,
    TradingActivity,
    PortfolioHolding,
)

# User schemas
from .users import (
    # User Management
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,
    UserSummary,
    
    # Authentication
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    EmailVerificationRequest,
    
    # Social Connections
    SocialConnectionBase,
    SocialConnectionCreate,
    SocialConnectionUpdate,
    SocialConnectionResponse,
    
    # Subscriptions
    UserSubscriptionBase,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    UserSubscriptionResponse,
    SubscriptionPlan,
    
    # Notifications
    UserNotificationBase,
    UserNotificationCreate,
    UserNotificationUpdate,
    UserNotificationResponse,
    
    # Preferences
    UserPreferencesBase,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    
    # Search and Filters
    UserSearchParams,
    
    # Bulk Operations
    BulkUserCreate,
    BulkUserUpdate,
    
    # Analytics
    UserAnalytics,
)

# Social media schemas
from .social import (
    # Social Posts
    SocialPostBase,
    SocialPostCreate,
    SocialPostUpdate,
    SocialPostResponse,
    
    # Post Templates
    PostTemplateBase,
    PostTemplateCreate,
    PostTemplateUpdate,
    PostTemplateResponse,
    
    # Automation
    AutomationRuleBase,
    AutomationRuleCreate,
    AutomationRuleUpdate,
    AutomationRuleResponse,
    
    # Engagement
    EngagementMetricBase,
    EngagementMetricCreate,
    EngagementMetricResponse,
    
    # Community
    CommunityPostBase,
    CommunityPostCreate,
    CommunityPostUpdate,
    CommunityPostResponse,
    CommunityCommentBase,
    CommunityCommentCreate,
    CommunityCommentUpdate,
    CommunityCommentResponse,
    
    # Search and Filters
    SocialPostSearchParams,
    CommunityPostSearchParams,
    
    # Analytics
    SocialAnalytics,
    CommunityAnalytics,
)

# Admin schemas
from .admin import (
    # System Monitoring
    SystemMetricsBase,
    SystemMetricsCreate,
    SystemMetricsResponse,
    SystemStatusResponse,
    
    # Audit Logging
    AuditLogBase,
    AuditLogCreate,
    AuditLogResponse,
    AuditLogSearchParams,
    
    # Analytics Dashboard
    DashboardMetrics,
    UserActivityMetrics,
    ContentModerationMetrics,
    
    # System Configuration
    ConfigurationBase,
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationResponse,
    
    # Feature Flags
    FeatureFlagBase,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    FeatureFlagResponse,
    
    # Data Management
    DataExportRequest,
    DataExportResponse,
    DataImportRequest,
    DataImportResponse,
    
    # Machine Learning
    MLModelBase,
    MLModelCreate,
    MLModelUpdate,
    MLModelResponse,
    MLPredictionBase,
    MLPredictionCreate,
    MLPredictionResponse,
)

# Convenience imports for common use cases
from .base import CapitolScopeBaseModel as BaseModel
from .securities import SecurityResponse as Security
from .congressional import CongressMemberResponse as CongressMember, CongressionalTradeResponse as CongressionalTrade
from .users import UserResponse as User

__all__ = [
    # Base
    "CapitolScopeBaseModel",
    "BaseModel",
    "UUIDMixin",
    "TimestampMixin",
    "PoliticalParty",
    "Chamber",
    "TransactionType",
    "SubscriptionTier",
    "SubscriptionStatus",
    "SocialPlatform",
    "PaginationParams",
    "SortParams",
    "PaginatedResponse",
    "APIResponse",
    "ErrorResponse",
    "AmountRange",
    "PerformanceMetrics",
    "TechnicalIndicators",
    "DateRangeFilter",
    "AmountFilter",
    "SearchParams",
    "SocialMediaLinks",
    "ResearchLinks",
    "NotificationPreferences",
    "HealthCheckResponse",
    "DetailedHealthCheckResponse",
    
    # Securities
    "AssetTypeBase",
    "AssetTypeCreate",
    "AssetTypeUpdate",
    "AssetTypeResponse",
    "SectorBase",
    "SectorCreate",
    "SectorUpdate",
    "SectorResponse",
    "ExchangeBase",
    "ExchangeCreate",
    "ExchangeUpdate",
    "ExchangeResponse",
    "SecurityBase",
    "SecurityCreate",
    "SecurityUpdate",
    "SecurityResponse",
    "Security",
    "SecuritySummary",
    "DailyPriceBase",
    "DailyPriceCreate",
    "DailyPriceResponse",
    "PriceHistory",
    "CorporateActionBase",
    "CorporateActionCreate",
    "CorporateActionUpdate",
    "CorporateActionResponse",
    "SecuritySearchParams",
    "PriceSearchParams",
    "BulkSecurityCreate",
    "BulkPriceCreate",
    "BulkOperationResponse",
    
    # Congressional
    "CongressMemberBase",
    "CongressMemberCreate",
    "CongressMemberUpdate",
    "CongressMemberResponse",
    "CongressMember",
    "CongressMemberSummary",
    "CongressionalTradeBase",
    "CongressionalTradeCreate",
    "CongressionalTradeUpdate",
    "CongressionalTradeResponse",
    "CongressionalTrade",
    "CongressionalTradeSummary",
    "CongressMemberSearchParams",
    "CongressionalTradeSearchParams",
    "BulkCongressMemberCreate",
    "BulkCongressionalTradeCreate",
    "MemberTradingStats",
    "TradingActivity",
    "PortfolioHolding",
    
    # Users
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "User",
    "UserProfile",
    "UserSummary",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordChangeRequest",
    "EmailVerificationRequest",
    "SocialConnectionBase",
    "SocialConnectionCreate",
    "SocialConnectionUpdate",
    "SocialConnectionResponse",
    "UserSubscriptionBase",
    "UserSubscriptionCreate",
    "UserSubscriptionUpdate",
    "UserSubscriptionResponse",
    "SubscriptionPlan",
    "UserNotificationBase",
    "UserNotificationCreate",
    "UserNotificationUpdate",
    "UserNotificationResponse",
    "UserPreferencesBase",
    "UserPreferencesCreate",
    "UserPreferencesUpdate",
    "UserPreferencesResponse",
    "UserSearchParams",
    "BulkUserCreate",
    "BulkUserUpdate",
    "UserAnalytics",
    
    # Social
    "SocialPostBase",
    "SocialPostCreate",
    "SocialPostUpdate",
    "SocialPostResponse",
    "PostTemplateBase",
    "PostTemplateCreate",
    "PostTemplateUpdate",
    "PostTemplateResponse",
    "AutomationRuleBase",
    "AutomationRuleCreate",
    "AutomationRuleUpdate",
    "AutomationRuleResponse",
    "EngagementMetricBase",
    "EngagementMetricCreate",
    "EngagementMetricResponse",
    "CommunityPostBase",
    "CommunityPostCreate",
    "CommunityPostUpdate",
    "CommunityPostResponse",
    "CommunityCommentBase",
    "CommunityCommentCreate",
    "CommunityCommentUpdate",
    "CommunityCommentResponse",
    "SocialPostSearchParams",
    "CommunityPostSearchParams",
    "SocialAnalytics",
    "CommunityAnalytics",
    
    # Admin
    "SystemMetricsBase",
    "SystemMetricsCreate",
    "SystemMetricsResponse",
    "SystemStatusResponse",
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogResponse",
    "AuditLogSearchParams",
    "DashboardMetrics",
    "UserActivityMetrics",
    "ContentModerationMetrics",
    "ConfigurationBase",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationResponse",
    "FeatureFlagBase",
    "FeatureFlagCreate",
    "FeatureFlagUpdate",
    "FeatureFlagResponse",
    "DataExportRequest",
    "DataExportResponse",
    "DataImportRequest",
    "DataImportResponse",
    "MLModelBase",
    "MLModelCreate",
    "MLModelUpdate",
    "MLModelResponse",
    "MLPredictionBase",
    "MLPredictionCreate",
    "MLPredictionResponse",
    
    # Validators
    "validate_ticker_symbol",
    "validate_political_party",
    "validate_chamber",
    "validate_transaction_type",
] 