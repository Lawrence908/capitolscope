"""
Congressional domain Pydantic schemas.

This module contains request/response schemas for congress members, trades,
and portfolio tracking. Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, validator, model_validator
from pydantic.types import NonNegativeInt, PositiveInt

from domains.base.schemas import CapitolScopeBaseSchema, PaginatedResponse, TimestampMixin
from domains.base.schemas import PoliticalParty, Chamber, TransactionType
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class TradeOwner(str, Enum):
    """Trade owner types."""
    SELF = "C"
    SPOUSE = "SP" 
    JOINT = "JT"
    DEPENDENT_CHILD = "DC"


class FilingStatus(str, Enum):
    """Filing status types."""
    NEW = "N"
    PARTIAL = "P"
    AMENDMENT = "A"


class SortField(str, Enum):
    """Available sort fields for trade queries."""
    TRANSACTION_DATE = "transaction_date"
    NOTIFICATION_DATE = "notification_date"
    AMOUNT = "amount"
    MEMBER_NAME = "member_name"
    TICKER = "ticker"
    TRANSACTION_TYPE = "transaction_type"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# CONGRESS MEMBER SCHEMAS
# ============================================================================

class CongressMemberBase(CapitolScopeBaseSchema):
    """Base congress member schema."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=200)
    prefix: Optional[str] = Field(None, max_length=10, description="Honorifics like 'Rep.', 'Sen.', 'Dr.', 'Mr.', 'Ms.'")
    party: Optional[PoliticalParty] = None
    chamber: Optional[Chamber] = None  # Made optional for import, will be populated via external APIs
    state: Optional[str] = Field(None, min_length=2, max_length=2, description="Two-letter state code")
    district: Optional[str] = Field(None, max_length=10)
    
    @validator('state')
    def validate_state(cls, v):
        if v and not v.isupper():
            raise ValueError('State code must be uppercase')
        return v


class CongressMemberCreate(CongressMemberBase):
    """Schema for creating a congress member."""
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    office_address: Optional[str] = None
    bioguide_id: Optional[str] = Field(None, max_length=10)
    congress_gov_id: Optional[str] = Field(None, max_length=20, description="ID from Congress.gov API")
    
    # Congress.gov API Data
    congress_gov_url: Optional[str] = Field(None, max_length=500, description="Direct link to member's Congress.gov page")
    image_url: Optional[str] = Field(None, max_length=500, description="Official member photo URL")
    image_attribution: Optional[str] = Field(None, max_length=200, description="Photo credit/source")
    last_api_update: Optional[datetime] = Field(None, description="When Congress.gov last updated this member")
    
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    congress_number: Optional[int] = Field(None, ge=1, le=200)
    is_active: bool = True  # Add is_active field


class CongressMemberUpdate(CapitolScopeBaseSchema):
    """Schema for updating a congress member."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    party: Optional[PoliticalParty] = None
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    office_address: Optional[str] = None
    congress_gov_id: Optional[str] = Field(None, max_length=20, description="ID from Congress.gov API")
    
    # Congress.gov API Data
    congress_gov_url: Optional[str] = Field(None, max_length=500, description="Direct link to member's Congress.gov page")
    image_url: Optional[str] = Field(None, max_length=500, description="Official member photo URL")
    image_attribution: Optional[str] = Field(None, max_length=200, description="Photo credit/source")
    last_api_update: Optional[datetime] = Field(None, description="When Congress.gov last updated this member")
    
    term_start: Optional[date] = None
    term_end: Optional[date] = None


class CongressMemberSummary(CongressMemberBase, TimestampMixin):
    """Summary congress member schema for list views."""
    id: UUID
    age: Optional[int] = None
    profession: Optional[str] = None
    
    # Computed fields
    trade_count: Optional[int] = Field(None, description="Total number of trades")
    total_trade_value: Optional[int] = Field(None, description="Total trade value in cents")
    portfolio_value: Optional[int] = Field(None, description="Current portfolio value in cents")
    
    model_config = {"from_attributes": True}


class CongressMemberDetail(CongressMemberSummary):
    """Detailed congress member schema."""
    email: Optional[str] = None
    phone: Optional[str] = None
    office_address: Optional[str] = None
    bioguide_id: Optional[str] = None
    congress_gov_id: Optional[str] = None
    
    # Congress.gov API Data
    congress_gov_url: Optional[str] = None
    image_url: Optional[str] = None
    image_attribution: Optional[str] = None
    last_api_update: Optional[datetime] = None
    
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    congress_number: Optional[int] = None
    education: Optional[str] = None
    committees: Optional[List[str]] = None
    leadership_roles: Optional[List[str]] = None
    twitter_handle: Optional[str] = None
    facebook_url: Optional[str] = None
    website_url: Optional[str] = None
    seniority_rank: Optional[int] = None
    vote_percentage: Optional[Decimal] = None
    influence_score: Optional[Decimal] = None
    fundraising_total: Optional[int] = None
    pac_contributions: Optional[int] = None
    
    # Research links
    wikipedia_url: Optional[str] = None
    ballotpedia_url: Optional[str] = None
    opensecrets_url: Optional[str] = None
    govtrack_id: Optional[str] = None
    votesmart_id: Optional[str] = None
    fec_id: Optional[str] = None


class CongressMemberPortfolioSummary(CapitolScopeBaseSchema):
    """Portfolio summary for a congress member."""
    member_id: UUID
    total_value: int = Field(..., description="Total portfolio value in cents")
    total_cost_basis: int = Field(..., description="Total cost basis in cents")
    unrealized_gain_loss: int = Field(..., description="Unrealized gain/loss in cents")
    realized_gain_loss: int = Field(..., description="Realized gain/loss in cents")
    position_count: int = Field(..., description="Number of positions")
    
    # Performance metrics
    total_return_percent: Optional[float] = Field(None, description="Total return percentage")
    daily_return: Optional[Decimal] = Field(None, description="Daily return percentage")
    
    model_config = {"from_attributes": True}


# ============================================================================
# CONGRESSIONAL TRADE SCHEMAS
# ============================================================================

class CongressionalTradeBase(CapitolScopeBaseSchema):
    """Base congressional trade schema."""
    member_id: UUID = Field(...)
    doc_id: str = Field(..., min_length=1, max_length=50)
    raw_asset_description: str = Field(..., min_length=1)
    transaction_type: TransactionType
    transaction_date: Optional[date] = None
    notification_date: Optional[date] = None
    
    @validator('notification_date')
    def validate_notification_date(cls, v, values):
        if v and 'transaction_date' in values and values['transaction_date'] and v < values['transaction_date']:
            raise ValueError('Notification date cannot be before transaction date')
        return v


class CongressionalTradeCreate(CongressionalTradeBase):
    """Schema for creating a congressional trade."""
    security_id: Optional[UUID] = None
    document_url: Optional[str] = Field(None, max_length=500)
    owner: Optional[TradeOwner] = None
    ticker: Optional[str] = Field(None, max_length=20)
    asset_name: Optional[str] = Field(None, max_length=300)
    asset_type: Optional[str] = Field(None, max_length=100)
    amount_min: Optional[int] = Field(None, ge=0, description="Minimum amount in cents")
    amount_max: Optional[int] = Field(None, ge=0, description="Maximum amount in cents")
    amount_exact: Optional[int] = Field(None, ge=0, description="Exact amount in cents")
    filing_status: Optional[FilingStatus] = None
    comment: Optional[str] = None
    cap_gains_over_200: bool = False
    
    @model_validator(mode='after')
    def validate_amounts(self):
        amount_min = self.amount_min
        amount_max = self.amount_max
        amount_exact = self.amount_exact
        
        # Must have at least one amount field, but can be all None for unknown amounts
        has_exact = amount_exact is not None
        has_range = amount_min is not None or amount_max is not None
        
        if not has_exact and not has_range:
            # Allow trades with no amount information
            return self
        
        # If we have a range, validate it
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            raise ValueError('Minimum amount cannot be greater than maximum amount')
        
        return self


class CongressionalTradeUpdate(CapitolScopeBaseSchema):
    """Schema for updating a congressional trade."""
    security_id: Optional[UUID] = None
    ticker: Optional[str] = Field(None, max_length=20)
    asset_name: Optional[str] = Field(None, max_length=300)
    asset_type: Optional[str] = Field(None, max_length=100)
    amount_exact: Optional[int] = Field(None, ge=0)
    ticker_confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    amount_confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    parsed_successfully: Optional[bool] = None
    parsing_notes: Optional[str] = None


class CongressionalTradeSummary(CongressionalTradeBase, TimestampMixin):
    """Summary congressional trade schema for list views."""
    id: UUID
    security_id: Optional[UUID] = None
    owner: Optional[TradeOwner] = None
    ticker: Optional[str] = None
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    estimated_value: Optional[int] = Field(None, description="Estimated trade value in cents")
    filing_status: Optional[FilingStatus] = None
    
    # Member information (joined)
    member_name: Optional[str] = None
    member_party: Optional[PoliticalParty] = None
    member_chamber: Optional[Chamber] = None
    member_state: Optional[str] = None
    
    model_config = {"from_attributes": True}


class CongressionalTradeDetail(CongressionalTradeSummary):
    """Detailed congressional trade schema."""
    document_url: Optional[str] = None
    amount_min: Optional[int] = None
    amount_max: Optional[int] = None
    amount_exact: Optional[int] = None
    comment: Optional[str] = None
    cap_gains_over_200: bool = False
    ticker_confidence: Optional[Decimal] = None
    amount_confidence: Optional[Decimal] = None
    parsed_successfully: bool = True
    parsing_notes: Optional[str] = None
    
    # Market data at time of trade
    market_cap_at_trade: Optional[int] = None
    price_at_trade: Optional[int] = None
    volume_at_trade: Optional[int] = None
    
    # Performance tracking
    price_change_1d: Optional[Decimal] = None
    price_change_7d: Optional[Decimal] = None
    price_change_30d: Optional[Decimal] = None
    
    # Computed fields
    days_to_disclosure: Optional[int] = Field(None, description="Days between trade and disclosure")


class CongressionalTradeWithMember(CongressionalTradeDetail):
    """Congressional trade with full member details."""
    member: CongressMemberSummary


# ============================================================================
# PORTFOLIO SCHEMAS
# ============================================================================

class MemberPortfolioBase(CapitolScopeBaseSchema):
    """Base member portfolio schema."""
    member_id: UUID = Field(...)
    security_id: UUID = Field(...)
    shares: Decimal = Field(..., ge=0, decimal_places=6)
    cost_basis: int = Field(..., ge=0, description="Total cost basis in cents")


class MemberPortfolioSummary(MemberPortfolioBase, TimestampMixin):
    """Summary member portfolio schema."""
    id: UUID
    avg_cost_per_share: Optional[int] = None
    first_purchase_date: Optional[date] = None
    last_transaction_date: Optional[date] = None
    total_purchases: int = 0
    total_sales: int = 0
    unrealized_gain_loss: Optional[int] = None
    realized_gain_loss: int = 0
    position_size_percent: Optional[Decimal] = None
    holding_period_days: Optional[int] = None
    
    # Security information (joined)
    security_ticker: Optional[str] = None
    security_name: Optional[str] = None
    current_price: Optional[int] = None
    
    # Computed fields
    current_value: Optional[int] = Field(None, description="Current position value in cents")
    
    model_config = {"from_attributes": True}


class MemberPortfolioDetail(MemberPortfolioSummary):
    """Detailed member portfolio schema with full security information."""
    # This would include full security details when needed
    pass


class PortfolioPerformanceBase(CapitolScopeBaseSchema):
    """Base portfolio performance schema."""
    member_id: UUID = Field(...)
    date: date
    total_value: int = Field(..., description="Total portfolio value in cents")
    total_cost_basis: int = Field(..., description="Total cost basis in cents")
    unrealized_gain_loss: int = Field(..., description="Unrealized gain/loss in cents")
    realized_gain_loss: int = Field(..., description="Realized gain/loss in cents")


class PortfolioPerformanceSummary(PortfolioPerformanceBase, TimestampMixin):
    """Summary portfolio performance schema."""
    id: UUID
    daily_return: Optional[Decimal] = None
    daily_gain_loss: Optional[int] = None
    benchmark_return: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    position_count: int = 0
    
    # Computed fields
    total_return_percent: Optional[float] = Field(None, description="Total return percentage")
    
    model_config = {"from_attributes": True}


class PortfolioPerformanceDetail(PortfolioPerformanceSummary):
    """Detailed portfolio performance schema."""
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sector_allocation: Optional[Dict[str, float]] = None
    top_holdings: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# QUERY SCHEMAS
# ============================================================================

class CongressionalTradeFilter(CapitolScopeBaseSchema):
    """Filters for congressional trade queries."""
    member_ids: Optional[List[UUID]] = Field(None, description="Filter by member IDs")
    member_names: Optional[List[str]] = Field(None, description="Filter by member names")
    parties: Optional[List[PoliticalParty]] = Field(None, description="Filter by political parties")
    chambers: Optional[List[Chamber]] = Field(None, description="Filter by chambers")
    states: Optional[List[str]] = Field(None, description="Filter by states")
    
    tickers: Optional[List[str]] = Field(None, description="Filter by ticker symbols")
    asset_types: Optional[List[str]] = Field(None, description="Filter by asset types")
    transaction_types: Optional[List[TransactionType]] = Field(None, description="Filter by transaction types")
    owners: Optional[List[TradeOwner]] = Field(None, description="Filter by trade owners")
    
    # Date ranges
    transaction_date_from: Optional[date] = None
    transaction_date_to: Optional[date] = None
    notification_date_from: Optional[date] = None
    notification_date_to: Optional[date] = None
    
    # Amount ranges (in cents)
    amount_min: Optional[int] = Field(None, ge=0, description="Minimum trade amount in cents")
    amount_max: Optional[int] = Field(None, ge=0, description="Maximum trade amount in cents")
    
    # Search
    search: Optional[str] = Field(None, min_length=1, description="Search across asset names and descriptions")
    
    @validator('amount_max')
    def validate_amount_range(cls, v, values):
        if v and 'amount_min' in values and values['amount_min'] and v < values['amount_min']:
            raise ValueError('Maximum amount cannot be less than minimum amount')
        return v


class CongressionalTradeQuery(CongressionalTradeFilter):
    """Query parameters for congressional trades."""
    sort_by: SortField = SortField.TRANSACTION_DATE
    sort_order: SortOrder = SortOrder.DESC
    page: PositiveInt = 1
    limit: int = Field(50, ge=1, le=1000)
    
    # Include related data
    include_member: bool = False
    include_security: bool = False
    include_performance: bool = False


class MemberQuery(CapitolScopeBaseSchema):
    """Query parameters for congress members."""
    parties: Optional[List[PoliticalParty]] = None
    chambers: Optional[List[Chamber]] = None
    states: Optional[List[str]] = None
    congress_numbers: Optional[List[int]] = None
    search: Optional[str] = Field(None, min_length=1)
    sort_by: str = "last_name"
    sort_order: SortOrder = SortOrder.ASC
    page: PositiveInt = 1
    limit: int = Field(50, ge=1, le=1000)
    
    # Include computed fields
    include_trade_stats: bool = False
    include_portfolio_value: bool = False


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class CongressionalTradeListResponse(PaginatedResponse):
    """Response schema for congressional trade list."""
    data: List[CongressionalTradeSummary]


class CongressionalTradeDetailResponse(CapitolScopeBaseSchema):
    """Response schema for congressional trade detail."""
    data: CongressionalTradeDetail


class CongressMemberListResponse(PaginatedResponse):
    """Response schema for congress member list."""
    data: List[CongressMemberSummary]


class CongressMemberDetailResponse(CapitolScopeBaseSchema):
    """Response schema for congress member detail."""
    data: CongressMemberDetail


class MemberPortfolioListResponse(PaginatedResponse):
    """Response schema for member portfolio list."""
    data: List[MemberPortfolioSummary]


class PortfolioPerformanceListResponse(PaginatedResponse):
    """Response schema for portfolio performance list."""
    data: List[PortfolioPerformanceSummary]


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class TradingStatistics(CapitolScopeBaseSchema):
    """Trading statistics for a member or group."""
    total_trades: int = 0
    total_value: int = Field(0, description="Total trade value in cents")
    purchase_count: int = 0
    sale_count: int = 0
    purchase_value: int = Field(0, description="Total purchase value in cents")
    sale_value: int = Field(0, description="Total sale value in cents")
    avg_trade_size: Optional[int] = Field(None, description="Average trade size in cents")
    avg_days_to_disclosure: Optional[float] = None
    most_traded_assets: Optional[List[Dict[str, Any]]] = None


class MarketPerformanceComparison(CapitolScopeBaseSchema):
    """Performance comparison with market benchmarks."""
    period_days: int
    portfolio_return: Decimal = Field(..., description="Portfolio return percentage")
    benchmark_return: Decimal = Field(..., description="Benchmark return percentage")
    alpha: Decimal = Field(..., description="Alpha vs benchmark")
    beta: Optional[Decimal] = Field(None, description="Beta vs benchmark")
    sharpe_ratio: Optional[Decimal] = None
    outperformed: bool = Field(..., description="Whether portfolio outperformed benchmark")


class MemberAnalytics(CapitolScopeBaseSchema):
    """Comprehensive analytics for a congress member."""
    member_id: UUID
    trading_stats: TradingStatistics
    portfolio_summary: Optional[CongressMemberPortfolioSummary] = None
    performance_1m: Optional[MarketPerformanceComparison] = None
    performance_3m: Optional[MarketPerformanceComparison] = None
    performance_1y: Optional[MarketPerformanceComparison] = None
    top_positions: Optional[List[MemberPortfolioSummary]] = None
    recent_trades: Optional[List[CongressionalTradeSummary]] = None


# Log schema creation
logger.info("Congressional domain schemas initialized")

# Export all schemas
__all__ = [
    # Enums
    "TradeOwner", "FilingStatus", "SortField", "SortOrder",
    
    # Member schemas
    "CongressMemberBase", "CongressMemberCreate", "CongressMemberUpdate",
    "CongressMemberSummary", "CongressMemberDetail", "CongressMemberPortfolioSummary",
    
    # Trade schemas
    "CongressionalTradeBase", "CongressionalTradeCreate", "CongressionalTradeUpdate",
    "CongressionalTradeSummary", "CongressionalTradeDetail", "CongressionalTradeWithMember",
    
    # Portfolio schemas
    "MemberPortfolioBase", "MemberPortfolioSummary", "MemberPortfolioDetail",
    "PortfolioPerformanceBase", "PortfolioPerformanceSummary", "PortfolioPerformanceDetail",
    
    # Query schemas
    "CongressionalTradeFilter", "CongressionalTradeQuery", "MemberQuery",
    
    # Response schemas
    "CongressionalTradeListResponse", "CongressionalTradeDetailResponse",
    "CongressMemberListResponse", "CongressMemberDetailResponse",
    "MemberPortfolioListResponse", "PortfolioPerformanceListResponse",
    
    # Analytics schemas
    "TradingStatistics", "MarketPerformanceComparison", "MemberAnalytics"
] 