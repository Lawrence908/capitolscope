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
    
    # Validators
    validate_ticker_symbol,
    validate_political_party,
    validate_chamber,
    validate_transaction_type,
)

# Health check schemas from base domain
from domains.base.schemas import (
    BasicHealthResponse,
    LivenessResponse,
    ReadinessResponse,
    DatabaseHealth,
    RedisHealth,
    CongressAPIHealth,
    ServiceChecks,
    ConfigurationInfo,
    DetailedHealthResponse,
    SystemMetrics,
    SystemPerformanceMetrics,
    SystemStatusResponse,
    # Legacy aliases
    HealthCheckResponse,
    DetailedHealthCheckResponse,
)

# Securities schemas from domain
from domains.securities.schemas import (
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
    DailyPriceUpdate,
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
    
    # Watchlists
    SecurityWatchlistBase,
    SecurityWatchlistCreate,
    SecurityWatchlistUpdate,
    SecurityWatchlistResponse,
)

# Congressional schemas from domain
from domains.congressional.schemas import (
    # Congress Members
    CongressMemberBase,
    CongressMemberCreate,
    CongressMemberUpdate,
    CongressMemberDetail as CongressMemberResponse,
    CongressMemberSummary,
    
    # Congressional Trades
    CongressionalTradeBase,
    CongressionalTradeCreate,
    CongressionalTradeUpdate,
    CongressionalTradeDetail as CongressionalTradeResponse,
    CongressionalTradeSummary,
    
    # Member Portfolios
    MemberPortfolioBase,
    MemberPortfolioSummary,
    MemberPortfolioDetail,
    
    # Portfolio Performance
    PortfolioPerformanceBase,
    PortfolioPerformanceSummary,
    PortfolioPerformanceDetail,
    
    # Search and Filters
    CongressionalTradeFilter,
    CongressionalTradeQuery,
    MemberQuery,
    
    # Response Schemas
    CongressionalTradeListResponse,
    CongressionalTradeDetailResponse,
    CongressMemberListResponse,
    CongressMemberDetailResponse,
    MemberPortfolioListResponse,
    PortfolioPerformanceListResponse,
    
    # Analytics
    TradingStatistics as MemberTradingStats,
    MarketPerformanceComparison,
    MemberAnalytics,
    
    # Enums
    TradeOwner,
    FilingStatus,
    SortField,
    SortOrder,
)

# User schemas from domain
from domains.users.schemas import (
    # User Management
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfileResponse as UserProfile,
    UserPreferenceResponse as UserPreferencesResponse,
    
    # Authentication
    LoginRequest,
    TokenResponse as LoginResponse,
    RefreshTokenRequest,
    ResetPasswordRequest as PasswordResetRequest,
    ResetPasswordConfirmRequest as PasswordResetConfirm,
    ChangePasswordRequest as PasswordChangeRequest,
    
    # Subscriptions
    SubscriptionResponse,
    SubscriptionUpdate,
    
    # Notifications
    NotificationResponse as UserNotificationResponse,
    NotificationMarkReadRequest,
    
    # Preferences
    UserPreferenceUpdate as UserPreferencesUpdate,
    
    # Watchlists and Alerts
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    
    # Error handling
    ErrorResponse,
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

# Notification schemas from domain
from domains.notifications.schemas import (
    # Enums
    NotificationType,
    AlertType,
    DeliveryStatus,
    SubscriptionFrequency,
    
    # Subscriptions
    SubscriptionPreferences,
    UserSubscriptionResponse,
    SubscriptionUpdateRequest,
    SubscriptionUpdateResponse,
    
    # Alerts
    AlertConfiguration,
    AlertResponse,
    AlertHistoryItem,
    AlertHistoryResponse,
    AlertListResponse,
    
    # Newsletters
    NewsletterSubscription,
    NewsletterSubscriptionRequest,
    NewsletterUnsubscribeRequest,
    NewsletterUnsubscribeResponse,
    NewsletterOptionsResponse,
    
    # Templates
    NotificationTemplate,
    TemplateListResponse,
    
    # Delivery
    DeliveryStats,
    DeliveryStatusResponse,
    
    # Testing
    TestNotificationRequest,
    TestNotificationResponse,
    
    # Analytics
    NotificationAnalytics,
    NotificationAnalyticsResponse,
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
from domains.securities.schemas import SecurityResponse as Security
from domains.congressional.schemas import CongressMemberDetail as CongressMember, CongressionalTradeDetail as CongressionalTrade
from domains.users.schemas import UserResponse as User

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
    # Health check schemas
    "BasicHealthResponse",
    "LivenessResponse",
    "ReadinessResponse",
    "DatabaseHealth",
    "RedisHealth",
    "CongressAPIHealth",
    "ServiceChecks",
    "ConfigurationInfo",
    "DetailedHealthResponse",
    "SystemMetrics",
    "SystemPerformanceMetrics",
    "SystemStatusResponse",
    # Legacy aliases
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
    "DailyPriceUpdate",
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
    "SecurityWatchlistBase",
    "SecurityWatchlistCreate",
    "SecurityWatchlistUpdate",
    "SecurityWatchlistResponse",
    
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
    "MemberPortfolioBase",
    "MemberPortfolioSummary",
    "MemberPortfolioDetail",
    "PortfolioPerformanceBase",
    "PortfolioPerformanceSummary",
    "PortfolioPerformanceDetail",
    "CongressionalTradeFilter",
    "CongressionalTradeQuery",
    "MemberQuery",
    "CongressionalTradeListResponse",
    "CongressionalTradeDetailResponse",
    "CongressMemberListResponse",
    "CongressMemberDetailResponse",
    "MemberPortfolioListResponse",
    "PortfolioPerformanceListResponse",
    "MemberTradingStats",
    "MarketPerformanceComparison",
    "MemberAnalytics",
    "TradeOwner",
    "FilingStatus",
    "SortField",
    "SortOrder",
    
    # Users
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "User",
    "UserProfile",
    "UserPreferencesResponse",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordChangeRequest",
    "SubscriptionResponse",
    "SubscriptionUpdate",
    "UserNotificationResponse",
    "NotificationMarkReadRequest",
    "UserPreferencesUpdate",
    "WatchlistCreate",
    "WatchlistUpdate",
    "WatchlistResponse",
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "ErrorResponse",
    
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
    
    # Notifications
    "NotificationType",
    "AlertType",
    "DeliveryStatus",
    "SubscriptionFrequency",
    "SubscriptionPreferences",
    "UserSubscriptionResponse",
    "SubscriptionUpdateRequest",
    "SubscriptionUpdateResponse",
    "AlertConfiguration",
    "AlertResponse",
    "AlertHistoryItem",
    "AlertHistoryResponse",
    "AlertListResponse",
    "NewsletterSubscription",
    "NewsletterSubscriptionRequest",
    "NewsletterUnsubscribeRequest",
    "NewsletterUnsubscribeResponse",
    "NewsletterOptionsResponse",
    "NotificationTemplate",
    "TemplateListResponse",
    "DeliveryStats",
    "DeliveryStatusResponse",
    "TestNotificationRequest",
    "TestNotificationResponse",
    "NotificationAnalytics",
    "NotificationAnalyticsResponse",
    
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