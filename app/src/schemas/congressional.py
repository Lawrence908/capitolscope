"""
Congressional members and trading data Pydantic schemas.

This module contains all schemas related to congress members,
their trades, and congressional data for the CapitolScope API.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from pydantic import Field, field_validator, EmailStr, HttpUrl

from schemas.base import (
    CapitolScopeBaseModel, UUIDMixin, TimestampMixin, AmountRange,
    PerformanceMetrics, SocialMediaLinks, ResearchLinks,
    validate_political_party, validate_chamber, validate_transaction_type
)
from schemas.securities import SecuritySummary


# ============================================================================
# CONGRESS MEMBERS
# ============================================================================

class CongressMemberBase(CapitolScopeBaseModel):
    """Base congress member schema."""
    first_name: str = Field(..., description="First name", max_length=100)
    last_name: str = Field(..., description="Last name", max_length=100)
    party: str = Field(..., description="Political party (D/R/I)", max_length=1)
    chamber: str = Field(..., description="Chamber (House/Senate)", max_length=10)
    state: str = Field(..., description="State abbreviation", max_length=2)
    district: Optional[str] = Field(None, description="District number (House only)", max_length=5)
    
    # Contact and Bio
    email: Optional[EmailStr] = Field(None, description="Official email address")
    phone: Optional[str] = Field(None, description="Phone number", max_length=20)
    office_address: Optional[str] = Field(None, description="Office address")
    
    # Terms and Status
    term_start: Optional[date] = Field(None, description="Current term start date")
    term_end: Optional[date] = Field(None, description="Current term end date")
    is_active: bool = Field(True, description="Currently serving")
    
    # Professional Background
    age: Optional[int] = Field(None, description="Age in years", ge=0, le=120)
    education: Optional[str] = Field(None, description="Educational background")
    profession: Optional[str] = Field(None, description="Previous profession")
    
    # Committee Information
    committees: Optional[List[str]] = Field(None, description="Committee memberships")
    leadership_roles: Optional[List[str]] = Field(None, description="Leadership positions")
    
    # Social Media and Research Links
    social_media: Optional[SocialMediaLinks] = Field(None, description="Social media profiles")
    research_links: Optional[ResearchLinks] = Field(None, description="Research and info links")
    
    # Congressional Data
    seniority_rank: Optional[int] = Field(None, description="Seniority ranking", ge=1)
    vote_percentage: Optional[float] = Field(None, description="Voting participation %", ge=0, le=100)
    
    # Premium Features
    influence_score: Optional[float] = Field(None, description="Calculated influence score", ge=0, le=100)
    fundraising_total: Optional[int] = Field(None, description="Total fundraising in cents", ge=0)
    pac_contributions: Optional[int] = Field(None, description="PAC contributions in cents", ge=0)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('party')
    @classmethod
    def validate_party(cls, v):
        """Validate political party."""
        return validate_political_party(v)
    
    @field_validator('chamber')
    @classmethod
    def validate_chamber(cls, v):
        """Validate chamber."""
        return validate_chamber(v)
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state code."""
        if len(v) != 2:
            raise ValueError('State must be 2-character abbreviation')
        return v.upper()


class CongressMemberCreate(CongressMemberBase):
    """Schema for creating congress members."""
    pass


class CongressMemberUpdate(CapitolScopeBaseModel):
    """Schema for updating congress members."""
    first_name: Optional[str] = Field(None, description="First name", max_length=100)
    last_name: Optional[str] = Field(None, description="Last name", max_length=100)
    party: Optional[str] = Field(None, description="Political party", max_length=1)
    chamber: Optional[str] = Field(None, description="Chamber", max_length=10)
    state: Optional[str] = Field(None, description="State abbreviation", max_length=2)
    district: Optional[str] = Field(None, description="District number", max_length=5)
    
    # Contact and Bio
    email: Optional[EmailStr] = Field(None, description="Official email address")
    phone: Optional[str] = Field(None, description="Phone number", max_length=20)
    office_address: Optional[str] = Field(None, description="Office address")
    
    # Terms and Status
    term_start: Optional[date] = Field(None, description="Current term start date")
    term_end: Optional[date] = Field(None, description="Current term end date")
    is_active: Optional[bool] = Field(None, description="Currently serving")
    
    # Professional Background
    age: Optional[int] = Field(None, description="Age in years", ge=0, le=120)
    education: Optional[str] = Field(None, description="Educational background")
    profession: Optional[str] = Field(None, description="Previous profession")
    
    # Committee Information
    committees: Optional[List[str]] = Field(None, description="Committee memberships")
    leadership_roles: Optional[List[str]] = Field(None, description="Leadership positions")
    
    # Social Media and Research Links
    social_media: Optional[SocialMediaLinks] = Field(None, description="Social media profiles")
    research_links: Optional[ResearchLinks] = Field(None, description="Research and info links")
    
    # Congressional Data
    seniority_rank: Optional[int] = Field(None, description="Seniority ranking", ge=1)
    vote_percentage: Optional[float] = Field(None, description="Voting participation %", ge=0, le=100)
    
    # Premium Features
    influence_score: Optional[float] = Field(None, description="Calculated influence score", ge=0, le=100)
    fundraising_total: Optional[int] = Field(None, description="Total fundraising in cents", ge=0)
    pac_contributions: Optional[int] = Field(None, description="PAC contributions in cents", ge=0)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CongressMemberResponse(CongressMemberBase, UUIDMixin, TimestampMixin):
    """Schema for congress member responses."""
    # Calculated fields
    full_name: Optional[str] = Field(None, description="Full name display")
    display_name: Optional[str] = Field(None, description="Display name with title")
    
    # Trading statistics
    total_trades: Optional[int] = Field(None, description="Total number of trades", ge=0)
    total_trade_value: Optional[int] = Field(None, description="Total trade value in cents", ge=0)
    last_trade_date: Optional[date] = Field(None, description="Date of last trade")
    
    # Performance metrics
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Portfolio performance")


class CongressMemberSummary(CapitolScopeBaseModel):
    """Lightweight congress member summary for lists."""
    id: int = Field(..., description="Member ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    party: str = Field(..., description="Political party")
    chamber: str = Field(..., description="Chamber")
    state: str = Field(..., description="State")
    district: Optional[str] = Field(None, description="District")
    total_trades: Optional[int] = Field(None, description="Total trades")
    last_trade_date: Optional[date] = Field(None, description="Last trade date")


# ============================================================================
# CONGRESSIONAL TRADES
# ============================================================================

class CongressionalTradeBase(CapitolScopeBaseModel):
    """Base congressional trade schema."""
    member_id: int = Field(..., description="Congress member ID")
    security_id: Optional[int] = Field(None, description="Security ID (if matched)")
    
    # Trade Details
    transaction_type: str = Field(..., description="Transaction type (P/S/E)")
    transaction_date: date = Field(..., description="Transaction date")
    disclosure_date: Optional[date] = Field(None, description="Disclosure date")
    
    # Asset Information
    ticker: Optional[str] = Field(None, description="Ticker symbol", max_length=20)
    asset_name: Optional[str] = Field(None, description="Asset name", max_length=300)
    asset_type: Optional[str] = Field(None, description="Asset type", max_length=100)
    
    # Amount Information
    amount_range: Optional[AmountRange] = Field(None, description="Transaction amount range")
    
    # Document Information
    document_url: Optional[HttpUrl] = Field(None, description="Source document URL")
    document_id: Optional[str] = Field(None, description="Document ID", max_length=100)
    
    # Processing Status
    is_processed: bool = Field(False, description="Whether trade has been processed")
    processing_notes: Optional[str] = Field(None, description="Processing notes")
    
    # ML Features
    market_cap_at_trade: Optional[int] = Field(None, description="Market cap at trade time", ge=0)
    price_at_trade: Optional[int] = Field(None, description="Price at trade time", ge=0)
    volume_at_trade: Optional[int] = Field(None, description="Volume at trade time", ge=0)
    
    # Performance tracking
    price_change_1d: Optional[float] = Field(None, description="Price change 1 day after")
    price_change_7d: Optional[float] = Field(None, description="Price change 7 days after")
    price_change_30d: Optional[float] = Field(None, description="Price change 30 days after")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('transaction_type')
    @classmethod
    def validate_transaction_type(cls, v):
        """Validate transaction type."""
        return validate_transaction_type(v)


class CongressionalTradeCreate(CongressionalTradeBase):
    """Schema for creating congressional trades."""
    pass


class CongressionalTradeUpdate(CapitolScopeBaseModel):
    """Schema for updating congressional trades."""
    security_id: Optional[int] = Field(None, description="Security ID")
    disclosure_date: Optional[date] = Field(None, description="Disclosure date")
    ticker: Optional[str] = Field(None, description="Ticker symbol", max_length=20)
    asset_name: Optional[str] = Field(None, description="Asset name", max_length=300)
    asset_type: Optional[str] = Field(None, description="Asset type", max_length=100)
    amount_range: Optional[AmountRange] = Field(None, description="Transaction amount range")
    document_url: Optional[HttpUrl] = Field(None, description="Source document URL")
    document_id: Optional[str] = Field(None, description="Document ID", max_length=100)
    is_processed: Optional[bool] = Field(None, description="Processing status")
    processing_notes: Optional[str] = Field(None, description="Processing notes")
    
    # ML Features
    market_cap_at_trade: Optional[int] = Field(None, description="Market cap at trade time", ge=0)
    price_at_trade: Optional[int] = Field(None, description="Price at trade time", ge=0)
    volume_at_trade: Optional[int] = Field(None, description="Volume at trade time", ge=0)
    
    # Performance tracking
    price_change_1d: Optional[float] = Field(None, description="Price change 1 day after")
    price_change_7d: Optional[float] = Field(None, description="Price change 7 days after")
    price_change_30d: Optional[float] = Field(None, description="Price change 30 days after")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CongressionalTradeResponse(CongressionalTradeBase, UUIDMixin, TimestampMixin):
    """Schema for congressional trade responses."""
    # Related objects (optional includes)
    member: Optional[CongressMemberSummary] = Field(None, description="Congress member details")
    security: Optional[SecuritySummary] = Field(None, description="Security details")
    
    # Calculated fields
    days_to_disclosure: Optional[int] = Field(None, description="Days between trade and disclosure")
    estimated_value: Optional[int] = Field(None, description="Estimated trade value in cents")


class CongressionalTradeSummary(CapitolScopeBaseModel):
    """Lightweight trade summary for lists."""
    id: int = Field(..., description="Trade ID")
    member_name: str = Field(..., description="Member name")
    ticker: Optional[str] = Field(None, description="Ticker symbol")
    asset_name: Optional[str] = Field(None, description="Asset name")
    transaction_type: str = Field(..., description="Transaction type")
    transaction_date: date = Field(..., description="Transaction date")
    estimated_value: Optional[int] = Field(None, description="Estimated value in cents")
    price_change_7d: Optional[float] = Field(None, description="7-day price change")


# ============================================================================
# SEARCH AND FILTER SCHEMAS
# ============================================================================

class CongressMemberSearchParams(CapitolScopeBaseModel):
    """Congress member search parameters."""
    query: Optional[str] = Field(None, description="Search query (name, state)", max_length=200)
    party: Optional[str] = Field(None, description="Political party filter", max_length=1)
    chamber: Optional[str] = Field(None, description="Chamber filter", max_length=10)
    state: Optional[str] = Field(None, description="State filter", max_length=2)
    is_active: Optional[bool] = Field(None, description="Active status filter")
    
    # Committee filters
    committee: Optional[str] = Field(None, description="Committee membership filter")
    leadership_role: Optional[str] = Field(None, description="Leadership role filter")
    
    # Trading activity filters
    has_trades: Optional[bool] = Field(None, description="Filter by trading activity")
    min_trade_count: Optional[int] = Field(None, description="Minimum trade count", ge=0)
    max_trade_count: Optional[int] = Field(None, description="Maximum trade count", ge=0)
    
    # Performance filters
    min_performance: Optional[float] = Field(None, description="Minimum performance %")
    max_performance: Optional[float] = Field(None, description="Maximum performance %")
    
    @field_validator('party')
    @classmethod
    def validate_party_filter(cls, v):
        """Validate party filter."""
        if v:
            return validate_political_party(v)
        return v
    
    @field_validator('chamber')
    @classmethod
    def validate_chamber_filter(cls, v):
        """Validate chamber filter."""
        if v:
            return validate_chamber(v)
        return v


class CongressionalTradeSearchParams(CapitolScopeBaseModel):
    """Congressional trade search parameters."""
    query: Optional[str] = Field(None, description="Search query (ticker, asset name)", max_length=200)
    member_ids: Optional[List[int]] = Field(None, description="Member IDs to filter by")
    security_ids: Optional[List[int]] = Field(None, description="Security IDs to filter by")
    
    # Date filters
    trade_date_start: Optional[date] = Field(None, description="Trade date start")
    trade_date_end: Optional[date] = Field(None, description="Trade date end")
    disclosure_date_start: Optional[date] = Field(None, description="Disclosure date start")
    disclosure_date_end: Optional[date] = Field(None, description="Disclosure date end")
    
    # Transaction filters
    transaction_types: Optional[List[str]] = Field(None, description="Transaction types (P/S/E)")
    min_amount: Optional[int] = Field(None, description="Minimum amount in cents", ge=0)
    max_amount: Optional[int] = Field(None, description="Maximum amount in cents", ge=0)
    
    # Asset filters
    asset_types: Optional[List[str]] = Field(None, description="Asset types to filter by")
    tickers: Optional[List[str]] = Field(None, description="Ticker symbols to filter by")
    
    # Processing filters
    is_processed: Optional[bool] = Field(None, description="Processing status filter")
    
    # Performance filters
    min_performance_1d: Optional[float] = Field(None, description="Minimum 1-day performance")
    max_performance_1d: Optional[float] = Field(None, description="Maximum 1-day performance")
    min_performance_7d: Optional[float] = Field(None, description="Minimum 7-day performance")
    max_performance_7d: Optional[float] = Field(None, description="Maximum 7-day performance")
    
    @field_validator('transaction_types')
    @classmethod
    def validate_transaction_types(cls, v):
        """Validate transaction types."""
        if v:
            for tx_type in v:
                validate_transaction_type(tx_type)
        return v
    
    @field_validator('trade_date_end')
    @classmethod
    def validate_trade_date_range(cls, v, values):
        """Validate trade date range."""
        start_date = values.get('trade_date_start')
        if start_date and v and v < start_date:
            raise ValueError('Trade end date must be after start date')
        return v
    
    @field_validator('disclosure_date_end')
    @classmethod
    def validate_disclosure_date_range(cls, v, values):
        """Validate disclosure date range."""
        start_date = values.get('disclosure_date_start')
        if start_date and v and v < start_date:
            raise ValueError('Disclosure end date must be after start date')
        return v


# ============================================================================
# BULK OPERATIONS
# ============================================================================

class BulkCongressMemberCreate(CapitolScopeBaseModel):
    """Schema for bulk creating congress members."""
    members: List[CongressMemberCreate] = Field(..., description="List of members to create")
    
    @field_validator('members')
    @classmethod
    def validate_members_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 1000:
            raise ValueError('Cannot create more than 1000 members at once')
        return v


class BulkCongressionalTradeCreate(CapitolScopeBaseModel):
    """Schema for bulk creating congressional trades."""
    trades: List[CongressionalTradeCreate] = Field(..., description="List of trades to create")
    
    @field_validator('trades')
    @classmethod
    def validate_trades_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 10000:
            raise ValueError('Cannot create more than 10000 trades at once')
        return v


# ============================================================================
# ANALYTICS AND REPORTING
# ============================================================================

class MemberTradingStats(CapitolScopeBaseModel):
    """Trading statistics for a congress member."""
    member_id: int = Field(..., description="Member ID")
    total_trades: int = Field(..., description="Total number of trades", ge=0)
    total_purchases: int = Field(..., description="Total purchases", ge=0)
    total_sales: int = Field(..., description="Total sales", ge=0)
    
    # Value statistics
    total_trade_value: int = Field(..., description="Total trade value in cents", ge=0)
    avg_trade_value: Optional[int] = Field(None, description="Average trade value in cents", ge=0)
    max_trade_value: Optional[int] = Field(None, description="Maximum trade value in cents", ge=0)
    
    # Performance metrics
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Performance metrics")
    
    # Timing statistics
    avg_disclosure_delay: Optional[float] = Field(None, description="Average disclosure delay in days")
    most_traded_sectors: Optional[List[str]] = Field(None, description="Most traded sectors")
    most_traded_assets: Optional[List[str]] = Field(None, description="Most traded assets")
    
    # Period information
    period_start: Optional[date] = Field(None, description="Statistics period start")
    period_end: Optional[date] = Field(None, description="Statistics period end")


class TradingActivity(CapitolScopeBaseModel):
    """Trading activity summary."""
    activity_date: date = Field(..., alias="date", description="Activity date")
    trade_count: int = Field(..., description="Number of trades", ge=0)
    member_count: int = Field(..., description="Number of active members", ge=0)
    total_value: int = Field(..., description="Total trade value in cents", ge=0)
    
    # Breakdown by type
    purchase_count: int = Field(..., description="Number of purchases", ge=0)
    sale_count: int = Field(..., description="Number of sales", ge=0)
    exchange_count: int = Field(..., description="Number of exchanges", ge=0)
    
    # Top assets
    top_assets: Optional[List[str]] = Field(None, description="Most traded assets")
    top_sectors: Optional[List[str]] = Field(None, description="Most traded sectors")


class PortfolioHolding(CapitolScopeBaseModel):
    """Portfolio holding information."""
    member_id: int = Field(..., description="Member ID")
    security_id: Optional[int] = Field(None, description="Security ID")
    ticker: Optional[str] = Field(None, description="Ticker symbol")
    asset_name: Optional[str] = Field(None, description="Asset name")
    
    # Position details
    total_shares: Optional[int] = Field(None, description="Total shares held", ge=0)
    average_cost: Optional[int] = Field(None, description="Average cost per share in cents", ge=0)
    current_value: Optional[int] = Field(None, description="Current value in cents", ge=0)
    
    # Performance
    unrealized_gain_loss: Optional[int] = Field(None, description="Unrealized gain/loss in cents")
    unrealized_gain_loss_percent: Optional[float] = Field(None, description="Unrealized gain/loss %")
    
    # Dates
    first_purchase_date: Optional[date] = Field(None, description="First purchase date")
    last_transaction_date: Optional[date] = Field(None, description="Last transaction date")
    
    # Metadata
    holding_period_days: Optional[int] = Field(None, description="Holding period in days", ge=0)
    position_size_percent: Optional[float] = Field(None, description="Position size % of portfolio") 