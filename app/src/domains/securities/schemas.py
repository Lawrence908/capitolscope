"""
Securities domain Pydantic schemas.

This module contains all schemas related to securities, asset types, exchanges,
and price data for the CapitolScope API.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import Field, field_validator

from domains.base.schemas import (
    CapitolScopeBaseSchema, UUIDMixin, TimestampMixin, TechnicalIndicators, TransactionType
)
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# ASSET TYPES
# ============================================================================

class AssetTypeBase(CapitolScopeBaseSchema):
    """Base asset type schema."""
    code: str = Field(..., description="Asset type code", max_length=5)
    name: str = Field(..., description="Asset type name", max_length=200)
    description: Optional[str] = Field(None, description="Asset type description")
    category: Optional[str] = Field(None, description="Asset category", max_length=50)
    risk_level: Optional[int] = Field(None, description="Risk level 1-5", ge=1, le=5)


class AssetTypeCreate(AssetTypeBase):
    """Schema for creating asset types."""
    pass


class AssetTypeUpdate(CapitolScopeBaseSchema):
    """Schema for updating asset types."""
    name: Optional[str] = Field(None, description="Asset type name", max_length=200)
    description: Optional[str] = Field(None, description="Asset type description")
    category: Optional[str] = Field(None, description="Asset category", max_length=50)
    risk_level: Optional[int] = Field(None, description="Risk level 1-5", ge=1, le=5)


class AssetTypeResponse(AssetTypeBase, UUIDMixin, TimestampMixin):
    """Schema for asset type responses."""
    securities_count: Optional[int] = Field(None, description="Number of securities", ge=0)


# ============================================================================
# SECTORS
# ============================================================================

class SectorBase(CapitolScopeBaseSchema):
    """Base sector schema."""
    gics_code: str = Field(..., description="GICS sector code", max_length=10)
    name: str = Field(..., description="Sector name", max_length=100)
    parent_sector_gics_code: Optional[str] = Field(None, description="Parent sector GICS code", max_length=10)
    market_sensitivity: Optional[float] = Field(None, description="Market beta sensitivity")
    volatility_score: Optional[float] = Field(None, description="Historical volatility score")


class SectorCreate(SectorBase):
    """Schema for creating sectors."""
    pass


class SectorUpdate(CapitolScopeBaseSchema):
    """Schema for updating sectors."""
    name: Optional[str] = Field(None, description="Sector name", max_length=100)
    parent_sector_gics_code: Optional[str] = Field(None, description="Parent sector GICS code", max_length=10)
    market_sensitivity: Optional[float] = Field(None, description="Market beta sensitivity")
    volatility_score: Optional[float] = Field(None, description="Historical volatility score")


class SectorResponse(SectorBase, UUIDMixin, TimestampMixin):
    """Schema for sector responses."""
    securities_count: Optional[int] = Field(None, description="Number of securities", ge=0)
    sub_sectors: Optional[List["SectorResponse"]] = Field(None, description="Sub-sectors")


# ============================================================================
# EXCHANGES
# ============================================================================

class ExchangeBase(CapitolScopeBaseSchema):
    """Base exchange schema."""
    code: str = Field(..., description="Exchange code", max_length=10)
    name: str = Field(..., description="Exchange name", max_length=100)
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-3)", max_length=3)
    timezone: str = Field(..., description="Exchange timezone", max_length=50)
    trading_hours: Optional[Dict[str, Any]] = Field(None, description="Trading hours configuration")
    market_cap_rank: Optional[int] = Field(None, description="Global market cap ranking", ge=1)


class ExchangeCreate(ExchangeBase):
    """Schema for creating exchanges."""
    pass


class ExchangeUpdate(CapitolScopeBaseSchema):
    """Schema for updating exchanges."""
    name: Optional[str] = Field(None, description="Exchange name", max_length=100)
    country: Optional[str] = Field(None, description="Country code", max_length=3)
    timezone: Optional[str] = Field(None, description="Exchange timezone", max_length=50)
    trading_hours: Optional[Dict[str, Any]] = Field(None, description="Trading hours")
    market_cap_rank: Optional[int] = Field(None, description="Market cap ranking", ge=1)


class ExchangeResponse(ExchangeBase, UUIDMixin, TimestampMixin):
    """Schema for exchange responses."""
    securities_count: Optional[int] = Field(None, description="Number of securities", ge=0)


# ============================================================================
# SECURITIES
# ============================================================================

class SecurityBase(CapitolScopeBaseSchema):
    """Base security schema."""
    ticker: str = Field(..., description="Security ticker symbol", max_length=20)
    name: str = Field(..., description="Security name", max_length=200)
    asset_type_code: Optional[str] = Field(None, description="Asset type code", max_length=5)
    sector_gics_code: Optional[str] = Field(None, description="Sector GICS code", max_length=10)
    exchange_code: Optional[str] = Field(None, description="Exchange code", max_length=10)
    currency: str = Field("USD", description="Currency code", max_length=3)
    market_cap: Optional[int] = Field(None, description="Market cap in cents", ge=0)
    shares_outstanding: Optional[int] = Field(None, description="Shares outstanding", ge=0)
    is_active: bool = Field(True, description="Whether security is actively traded")
    
    # Identifiers
    isin: Optional[str] = Field(None, description="ISIN identifier", max_length=12)
    cusip: Optional[str] = Field(None, description="CUSIP identifier", max_length=9)
    figi: Optional[str] = Field(None, description="FIGI identifier", max_length=12)
    
    # ML Features
    beta: Optional[float] = Field(None, description="Market beta")
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    dividend_yield: Optional[float] = Field(None, description="Annual dividend yield")
    volatility_30d: Optional[float] = Field(None, description="30-day volatility")
    volume_avg_30d: Optional[int] = Field(None, description="30-day average volume", ge=0)
    
    # ESG and Social Impact
    esg_score: Optional[float] = Field(None, description="ESG score", ge=0, le=100)
    controversy_score: Optional[float] = Field(None, description="Controversy score")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Validate ticker symbol format."""
        return validate_ticker_symbol(v)


class SecurityCreate(SecurityBase):
    """Schema for creating securities."""
    pass


class SecurityUpdate(CapitolScopeBaseSchema):
    """Schema for updating securities."""
    name: Optional[str] = Field(None, description="Security name", max_length=200)
    asset_type_code: Optional[str] = Field(None, description="Asset type code", max_length=5)
    sector_gics_code: Optional[str] = Field(None, description="Sector GICS code", max_length=10)
    exchange_code: Optional[str] = Field(None, description="Exchange code", max_length=10)
    currency: Optional[str] = Field(None, description="Currency code", max_length=3)
    market_cap: Optional[int] = Field(None, description="Market cap in cents", ge=0)
    shares_outstanding: Optional[int] = Field(None, description="Shares outstanding", ge=0)
    is_active: Optional[bool] = Field(None, description="Active trading status")
    
    # Identifiers
    isin: Optional[str] = Field(None, description="ISIN identifier", max_length=12)
    cusip: Optional[str] = Field(None, description="CUSIP identifier", max_length=9)
    figi: Optional[str] = Field(None, description="FIGI identifier", max_length=12)
    
    # ML Features
    beta: Optional[float] = Field(None, description="Market beta")
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    dividend_yield: Optional[float] = Field(None, description="Annual dividend yield")
    volatility_30d: Optional[float] = Field(None, description="30-day volatility")
    volume_avg_30d: Optional[int] = Field(None, description="30-day average volume", ge=0)
    
    # ESG and Social Impact
    esg_score: Optional[float] = Field(None, description="ESG score", ge=0, le=100)
    controversy_score: Optional[float] = Field(None, description="Controversy score")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SecurityResponse(SecurityBase, UUIDMixin, TimestampMixin):
    """Schema for security responses."""
    # Related object responses (optional includes)
    asset_type: Optional[AssetTypeResponse] = Field(None, description="Asset type details")
    sector: Optional[SectorResponse] = Field(None, description="Sector details")
    exchange: Optional[ExchangeResponse] = Field(None, description="Exchange details")
    
    # Current price data
    current_price: Optional[int] = Field(None, description="Current price in cents")
    price_change_24h: Optional[float] = Field(None, description="24h price change percentage")
    
    # Display helpers
    display_name: Optional[str] = Field(None, description="Formatted display name")
    market_cap_formatted: Optional[str] = Field(None, description="Formatted market cap")


class SecuritySummary(CapitolScopeBaseSchema):
    """Lightweight security summary for lists."""
    id: int = Field(..., description="Security ID")
    ticker: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Security name")
    current_price: Optional[int] = Field(None, description="Current price in cents")
    price_change_24h: Optional[float] = Field(None, description="24h price change percentage")
    market_cap: Optional[int] = Field(None, description="Market cap in cents")
    asset_type_name: Optional[str] = Field(None, description="Asset type name")
    sector_name: Optional[str] = Field(None, description="Sector name")


# ============================================================================
# PRICE DATA
# ============================================================================

class DailyPriceBase(CapitolScopeBaseSchema):
    """Base daily price schema."""
    security_id: int = Field(..., description="Security ID")
    price_date: date = Field(..., description="Price date")
    open_price: int = Field(..., description="Opening price in cents", ge=0)
    high_price: int = Field(..., description="High price in cents", ge=0)
    low_price: int = Field(..., description="Low price in cents", ge=0)
    close_price: int = Field(..., description="Closing price in cents", ge=0)
    adjusted_close: Optional[int] = Field(None, description="Adjusted close price in cents", ge=0)
    volume: int = Field(..., description="Trading volume", ge=0)
    
    # Technical indicators (optional)
    rsi_14: Optional[float] = Field(None, description="14-day RSI")
    macd: Optional[float] = Field(None, description="MACD value")
    bollinger_upper: Optional[int] = Field(None, description="Bollinger upper band (cents)")
    bollinger_lower: Optional[int] = Field(None, description="Bollinger lower band (cents)")
    
    @field_validator('high_price')
    @classmethod
    def validate_high_price(cls, v):
        """Ensure high price is >= 0."""
        if v < 0:
            raise ValueError('High price must be >= 0')
        return v
    
    @field_validator('low_price')
    @classmethod
    def validate_low_price(cls, v):
        """Ensure low price is >= 0."""
        if v < 0:
            raise ValueError('Low price must be >= 0')
        return v


class DailyPriceCreate(DailyPriceBase):
    """Schema for creating daily prices."""
    pass


class DailyPriceUpdate(CapitolScopeBaseSchema):
    """Schema for updating daily prices."""
    adjusted_close: Optional[int] = Field(None, description="Adjusted close price in cents", ge=0)
    rsi_14: Optional[float] = Field(None, description="14-day RSI")
    macd: Optional[float] = Field(None, description="MACD value")
    bollinger_upper: Optional[int] = Field(None, description="Bollinger upper band (cents)")
    bollinger_lower: Optional[int] = Field(None, description="Bollinger lower band (cents)")


class DailyPriceResponse(DailyPriceBase, UUIDMixin, TimestampMixin):
    """Schema for daily price responses."""
    # Technical indicators (if calculated)
    technical_indicators: Optional[TechnicalIndicators] = Field(None, description="Technical indicators")
    
    # Price change calculations
    price_change: Optional[int] = Field(None, description="Price change in cents")
    price_change_percent: Optional[float] = Field(None, description="Price change percentage")
    
    # Display helpers
    formatted_prices: Optional[Dict[str, str]] = Field(None, description="Formatted price strings")


class PriceHistory(CapitolScopeBaseSchema):
    """Price history for charts and analysis."""
    security_id: int = Field(..., description="Security ID")
    prices: List[DailyPriceResponse] = Field(..., description="List of daily prices")
    period: str = Field(..., description="Time period (1d, 1w, 1m, 3m, 6m, 1y, 5y)")
    total_return: Optional[float] = Field(None, description="Total return for period")
    volatility: Optional[float] = Field(None, description="Price volatility")
    
    # Summary statistics
    min_price: Optional[int] = Field(None, description="Minimum price in period")
    max_price: Optional[int] = Field(None, description="Maximum price in period")
    avg_volume: Optional[int] = Field(None, description="Average volume in period")


# ============================================================================
# CORPORATE ACTIONS
# ============================================================================

class CorporateActionBase(CapitolScopeBaseSchema):
    """Base corporate action schema."""
    security_id: int = Field(..., description="Security ID")
    action_type: str = Field(..., description="Action type (split, dividend, spinoff, merger)")
    ex_date: date = Field(..., description="Ex-dividend/ex-rights date")
    record_date: Optional[date] = Field(None, description="Record date")
    payment_date: Optional[date] = Field(None, description="Payment date")
    ratio: Optional[Decimal] = Field(None, description="Split ratio (e.g., 2.0 for 2:1)")
    amount: Optional[int] = Field(None, description="Dividend amount in cents", ge=0)
    description: Optional[str] = Field(None, description="Action description")
    
    # Impact tracking
    price_impact_1d: Optional[float] = Field(None, description="1-day price impact")
    volume_impact_1d: Optional[float] = Field(None, description="1-day volume impact")
    
    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v):
        """Validate action type."""
        valid_types = ['split', 'dividend', 'spinoff', 'merger', 'rights_offering']
        if v not in valid_types:
            raise ValueError(f'Action type must be one of: {valid_types}')
        return v


class CorporateActionCreate(CorporateActionBase):
    """Schema for creating corporate actions."""
    pass


class CorporateActionUpdate(CapitolScopeBaseSchema):
    """Schema for updating corporate actions."""
    record_date: Optional[date] = Field(None, description="Record date")
    payment_date: Optional[date] = Field(None, description="Payment date")
    ratio: Optional[Decimal] = Field(None, description="Split ratio")
    amount: Optional[int] = Field(None, description="Dividend amount in cents", ge=0)
    description: Optional[str] = Field(None, description="Action description")
    price_impact_1d: Optional[float] = Field(None, description="1-day price impact")
    volume_impact_1d: Optional[float] = Field(None, description="1-day volume impact")


class CorporateActionResponse(CorporateActionBase, UUIDMixin, TimestampMixin):
    """Schema for corporate action responses."""
    security: Optional[SecuritySummary] = Field(None, description="Security details")
    
    # Display helpers
    formatted_amount: Optional[str] = Field(None, description="Formatted dividend amount")
    formatted_ratio: Optional[str] = Field(None, description="Formatted split ratio")


# ============================================================================
# SEARCH AND FILTER SCHEMAS
# ============================================================================

class SecuritySearchParams(CapitolScopeBaseSchema):
    """Security search parameters."""
    query: Optional[str] = Field(None, description="Search query (ticker, name)", max_length=200)
    asset_type_codes: Optional[List[str]] = Field(None, description="Asset type codes to filter by")
    sector_gics_codes: Optional[List[str]] = Field(None, description="Sector GICS codes to filter by")
    exchange_codes: Optional[List[str]] = Field(None, description="Exchange codes to filter by")
    min_market_cap: Optional[int] = Field(None, description="Minimum market cap in cents", ge=0)
    max_market_cap: Optional[int] = Field(None, description="Maximum market cap in cents", ge=0)
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_options: Optional[bool] = Field(None, description="Filter by options availability")
    min_volume: Optional[int] = Field(None, description="Minimum daily volume", ge=0)
    
    @field_validator('max_market_cap')
    @classmethod
    def validate_market_cap_range(cls, v):
        """Ensure max market cap is valid."""
        if v and v < 0:
            raise ValueError('Maximum market cap must be greater than 0')
        return v


class PriceSearchParams(CapitolScopeBaseSchema):
    """Price data search parameters."""
    security_ids: Optional[List[int]] = Field(None, description="Security IDs")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    include_technical_indicators: bool = Field(False, description="Include technical indicators")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v):
        """Ensure end date is valid."""
        if v and v > date.today():
            raise ValueError('End date cannot be in the future')
        return v


# ============================================================================
# BULK OPERATIONS
# ============================================================================

class BulkSecurityCreate(CapitolScopeBaseSchema):
    """Schema for bulk creating securities."""
    securities: List[SecurityCreate] = Field(..., description="List of securities to create")
    
    @field_validator('securities')
    @classmethod
    def validate_securities_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 1000:
            raise ValueError('Cannot create more than 1000 securities at once')
        return v


class BulkPriceCreate(CapitolScopeBaseSchema):
    """Schema for bulk creating price data."""
    prices: List[DailyPriceCreate] = Field(..., description="List of prices to create")
    
    @field_validator('prices')
    @classmethod
    def validate_prices_limit(cls, v):
        """Limit bulk operations size."""
        if len(v) > 10000:
            raise ValueError('Cannot create more than 10000 prices at once')
        return v


class BulkOperationResponse(CapitolScopeBaseSchema):
    """Response for bulk operations."""
    total_requested: int = Field(..., description="Total items requested")
    total_created: int = Field(..., description="Total items created")
    total_updated: int = Field(..., description="Total items updated")
    total_failed: int = Field(..., description="Total items failed")
    errors: Optional[List[str]] = Field(None, description="List of error messages")
    created_ids: Optional[List[int]] = Field(None, description="IDs of created items")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


# ============================================================================
# WATCHLIST SCHEMAS
# ============================================================================

class SecurityWatchlistBase(CapitolScopeBaseSchema):
    """Base security watchlist schema."""
    security_id: int = Field(..., description="Security ID")
    notes: Optional[str] = Field(None, description="User notes")
    alert_price_target: Optional[int] = Field(None, description="Price target in cents")
    alert_enabled: bool = Field(False, description="Alert enabled status")


class SecurityWatchlistCreate(SecurityWatchlistBase):
    """Schema for creating security watchlists."""
    pass


class SecurityWatchlistUpdate(CapitolScopeBaseSchema):
    """Schema for updating security watchlists."""
    notes: Optional[str] = Field(None, description="User notes")
    alert_price_target: Optional[int] = Field(None, description="Price target in cents")
    alert_enabled: Optional[bool] = Field(None, description="Alert enabled status")


class SecurityWatchlistResponse(SecurityWatchlistBase, UUIDMixin, TimestampMixin):
    """Schema for security watchlist responses."""
    user_id: str = Field(..., description="User ID")
    security: Optional[SecuritySummary] = Field(None, description="Security details")
    
    # Alert status
    price_target_reached: Optional[bool] = Field(None, description="Price target reached")
    current_price: Optional[int] = Field(None, description="Current price in cents")


# Log schema initialization
logger.info("Securities domain schemas initialized")

# Export all schemas
__all__ = [
    "AssetTypeBase", "AssetTypeCreate", "AssetTypeUpdate", "AssetTypeResponse",
    "SectorBase", "SectorCreate", "SectorUpdate", "SectorResponse",
    "ExchangeBase", "ExchangeCreate", "ExchangeUpdate", "ExchangeResponse",
    "SecurityBase", "SecurityCreate", "SecurityUpdate", "SecurityResponse", "SecuritySummary",
    "DailyPriceBase", "DailyPriceCreate", "DailyPriceUpdate", "DailyPriceResponse", "PriceHistory",
    "CorporateActionBase", "CorporateActionCreate", "CorporateActionUpdate", "CorporateActionResponse",
    "SecuritySearchParams", "PriceSearchParams",
    "BulkSecurityCreate", "BulkPriceCreate", "BulkOperationResponse",
    "SecurityWatchlistBase", "SecurityWatchlistCreate", "SecurityWatchlistUpdate", "SecurityWatchlistResponse"
] 