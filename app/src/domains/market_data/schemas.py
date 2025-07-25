"""
Market data schemas for the CapitolScope API.

This module contains Pydantic schemas for market data, prices,
indices, economic indicators, and data feeds.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import Field, field_validator

from schemas.base import CapitolScopeBaseModel, UUIDMixin, TimestampMixin
from schemas.securities import SecuritySummary, DailyPriceResponse


# ============================================================================
# PRICE DATA SCHEMAS
# ============================================================================

class DailyPriceSummary(CapitolScopeBaseModel):
    """Daily price summary for lists."""
    security_id: int = Field(..., description="Security ID")
    symbol: str = Field(..., description="Stock symbol")
    price_date: date = Field(..., description="Price date")
    open_price: int = Field(..., description="Opening price in cents")
    high_price: int = Field(..., description="High price in cents")
    low_price: int = Field(..., description="Low price in cents")
    close_price: int = Field(..., description="Closing price in cents")
    volume: int = Field(..., description="Trading volume")
    price_change: Optional[int] = Field(None, description="Price change in cents")
    price_change_percent: Optional[float] = Field(None, description="Price change percentage")


class IntradayPrice(CapitolScopeBaseModel):
    """Intraday price data."""
    timestamp: datetime = Field(..., description="Price timestamp")
    open_price: int = Field(..., description="Opening price in cents")
    high_price: int = Field(..., description="High price in cents")
    low_price: int = Field(..., description="Low price in cents")
    close_price: int = Field(..., description="Closing price in cents")
    volume: int = Field(..., description="Trading volume")
    interval: str = Field(..., description="Time interval")


class SymbolPriceResponse(CapitolScopeBaseModel):
    """Symbol price response."""
    symbol: str = Field(..., description="Stock symbol")
    prices: List[DailyPriceResponse] = Field(default_factory=list, description="Price history")
    date_range: Dict[str, Any] = Field(default_factory=dict, description="Date range")
    technical_indicators: Optional[Dict[str, Any]] = Field(None, description="Technical indicators")
    statistics: Optional[Dict[str, Any]] = Field(None, description="Price statistics")
    enhanced_data: bool = Field(False, description="Enhanced data available")
    premium_features: bool = Field(False, description="Premium features available")


class IntradayPriceResponse(CapitolScopeBaseModel):
    """Intraday price response."""
    symbol: str = Field(..., description="Stock symbol")
    date: date = Field(..., description="Trading date")
    interval: str = Field(..., description="Time interval")
    prices: List[IntradayPrice] = Field(default_factory=list, description="Intraday prices")
    total: int = Field(0, description="Total price points")
    market_hours: Dict[str, str] = Field(default_factory=dict, description="Market hours")
    subscription_tier: str = Field(..., description="User subscription tier")


class PriceListResponse(CapitolScopeBaseModel):
    """Price list response."""
    prices: List[DailyPriceSummary] = Field(default_factory=list, description="Price data")
    total: int = Field(0, description="Total prices")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    includes: Dict[str, bool] = Field(default_factory=dict, description="Included features")
    enhanced_data: bool = Field(False, description="Enhanced data available")
    premium_features: bool = Field(False, description="Premium features available")
    user_tier: str = Field(..., description="User subscription tier")


# ============================================================================
# MARKET INDICES SCHEMAS
# ============================================================================

class MarketIndex(CapitolScopeBaseModel):
    """Market index data."""
    symbol: str = Field(..., description="Index symbol")
    name: str = Field(..., description="Index name")
    current_value: float = Field(..., description="Current index value")
    change: float = Field(..., description="Point change")
    change_percent: float = Field(..., description="Percentage change")
    volume: Optional[int] = Field(None, description="Trading volume")
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    last_updated: datetime = Field(..., description="Last update timestamp")


class IndexHistoryItem(CapitolScopeBaseModel):
    """Index history item."""
    date: date = Field(..., description="History date")
    open_value: float = Field(..., description="Opening value")
    high_value: float = Field(..., description="High value")
    low_value: float = Field(..., description="Low value")
    close_value: float = Field(..., description="Closing value")
    volume: Optional[int] = Field(None, description="Trading volume")


class IndexHistoryResponse(CapitolScopeBaseModel):
    """Index history response."""
    symbol: str = Field(..., description="Index symbol")
    history: List[IndexHistoryItem] = Field(default_factory=list, description="History data")
    date_range: Dict[str, Any] = Field(default_factory=dict, description="Date range")
    statistics: Dict[str, float] = Field(default_factory=dict, description="Performance statistics")


class IndexListResponse(CapitolScopeBaseModel):
    """Index list response."""
    indices: List[MarketIndex] = Field(default_factory=list, description="Market indices")
    total: int = Field(0, description="Total indices")
    filter: Dict[str, Any] = Field(default_factory=dict, description="Applied filter")
    includes: Dict[str, bool] = Field(default_factory=dict, description="Included features")
    enhanced_data: bool = Field(False, description="Enhanced data available")


# ============================================================================
# ECONOMIC INDICATORS SCHEMAS
# ============================================================================

class EconomicIndicator(CapitolScopeBaseModel):
    """Economic indicator data."""
    indicator_id: int = Field(..., description="Indicator ID")
    name: str = Field(..., description="Indicator name")
    category: str = Field(..., description="Indicator category")
    value: float = Field(..., description="Current value")
    previous_value: Optional[float] = Field(None, description="Previous value")
    change: Optional[float] = Field(None, description="Value change")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    unit: str = Field(..., description="Value unit")
    date: date = Field(..., description="Indicator date")
    frequency: str = Field(..., description="Update frequency")
    source: str = Field(..., description="Data source")


class EconomicIndicatorListResponse(CapitolScopeBaseModel):
    """Economic indicator list response."""
    indicators: List[EconomicIndicator] = Field(default_factory=list, description="Economic indicators")
    total: int = Field(0, description="Total indicators")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    categories: List[str] = Field(default_factory=list, description="Available categories")
    subscription_tier: str = Field(..., description="User subscription tier")


# ============================================================================
# TREASURY RATES SCHEMAS
# ============================================================================

class TreasuryRate(CapitolScopeBaseModel):
    """Treasury rate data."""
    maturity: str = Field(..., description="Maturity period")
    rate: float = Field(..., description="Interest rate")
    previous_rate: Optional[float] = Field(None, description="Previous rate")
    change: Optional[float] = Field(None, description="Rate change")
    date: date = Field(..., description="Rate date")


class YieldCurve(CapitolScopeBaseModel):
    """Yield curve data."""
    date: date = Field(..., description="Curve date")
    maturities: List[str] = Field(default_factory=list, description="Maturity periods")
    rates: List[float] = Field(default_factory=list, description="Interest rates")
    curve_type: str = Field(..., description="Curve type")


class TreasuryRatesResponse(CapitolScopeBaseModel):
    """Treasury rates response."""
    rates: List[TreasuryRate] = Field(default_factory=list, description="Treasury rates")
    yield_curve: Optional[YieldCurve] = Field(None, description="Yield curve data")
    spreads: Optional[Dict[str, float]] = Field(None, description="Rate spreads")
    date_range: Dict[str, Any] = Field(default_factory=dict, description="Date range")
    enhanced_data: bool = Field(False, description="Enhanced data available")


# ============================================================================
# DATA FEED SCHEMAS
# ============================================================================

class DataFeedStatus(CapitolScopeBaseModel):
    """Data feed status."""
    feed_id: int = Field(..., description="Feed ID")
    name: str = Field(..., description="Feed name")
    source: str = Field(..., description="Data source")
    status: str = Field(..., description="Feed status")
    last_update: Optional[datetime] = Field(None, description="Last update")
    next_update: Optional[datetime] = Field(None, description="Next scheduled update")
    error_count: int = Field(0, description="Error count")
    success_rate: float = Field(0.0, description="Success rate")
    data_quality_score: float = Field(0.0, description="Data quality score")


class DataFeedRefreshResponse(CapitolScopeBaseModel):
    """Data feed refresh response."""
    feed_id: int = Field(..., description="Feed ID")
    refresh_initiated: bool = Field(..., description="Refresh initiated")
    force: bool = Field(..., description="Force refresh")
    estimated_completion: str = Field(..., description="Estimated completion time")
    initiated_by: int = Field(..., description="User who initiated refresh")


class DataFeedStatusResponse(CapitolScopeBaseModel):
    """Data feed status response."""
    feeds: List[DataFeedStatus] = Field(default_factory=list, description="Data feeds")
    total_feeds: int = Field(0, description="Total feeds")
    healthy_feeds: int = Field(0, description="Healthy feeds")
    failed_feeds: int = Field(0, description="Failed feeds")
    last_update: datetime = Field(..., description="Last status update")
    overall_health: str = Field(..., description="Overall health status")
    data_quality_score: float = Field(0.0, description="Overall data quality score")


# ============================================================================
# MARKET HOLIDAYS SCHEMAS
# ============================================================================

class MarketHoliday(CapitolScopeBaseModel):
    """Market holiday data."""
    date: date = Field(..., description="Holiday date")
    name: str = Field(..., description="Holiday name")
    market: str = Field(..., description="Market name")
    is_holiday: bool = Field(..., description="Is trading holiday")
    trading_hours: Optional[Dict[str, str]] = Field(None, description="Trading hours")


class MarketHolidaysResponse(CapitolScopeBaseModel):
    """Market holidays response."""
    holidays: List[MarketHoliday] = Field(default_factory=list, description="Market holidays")
    year: int = Field(..., description="Year")
    market: str = Field(..., description="Market name")
    total: int = Field(0, description="Total holidays")
    next_holiday: Optional[MarketHoliday] = Field(None, description="Next holiday")
    trading_days_remaining: int = Field(0, description="Trading days remaining")


# ============================================================================
# SECURITY SEARCH SCHEMAS
# ============================================================================

class SecuritySearchResult(CapitolScopeBaseModel):
    """Security search result."""
    id: int = Field(..., description="Security ID")
    ticker: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Security name")
    asset_type: Optional[str] = Field(None, description="Asset type")
    sector: Optional[str] = Field(None, description="Sector")
    exchange: Optional[str] = Field(None, description="Exchange")
    current_price: Optional[int] = Field(None, description="Current price in cents")
    market_cap: Optional[int] = Field(None, description="Market cap in cents")
    volume: Optional[int] = Field(None, description="Trading volume")
    price_change_24h: Optional[float] = Field(None, description="24h price change")
    match_score: Optional[float] = Field(None, description="Search match score")


class SecuritySearchResponse(CapitolScopeBaseModel):
    """Security search response."""
    query: str = Field(..., description="Search query")
    results: List[SecuritySearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(0, description="Total results")
    limit: int = Field(0, description="Result limit")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    includes: Dict[str, bool] = Field(default_factory=dict, description="Included features")
    enhanced_data: bool = Field(False, description="Enhanced data available") 