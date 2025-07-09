"""
SQLAlchemy models for market data management.

This module defines the database models for tracking stock prices, market indices,
economic indicators, and data feeds for the CapitolScope platform.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, Time, Boolean, 
    Text, ForeignKey, Index, UniqueConstraint, CheckConstraint, JSON
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

from domains.base.models import BaseModel, TimestampMixin


class DailyPrice(BaseModel, TimestampMixin):
    """
    Daily OHLC (Open, High, Low, Close) price data for securities.
    
    Core table for historical price tracking and portfolio valuation.
    """
    __tablename__ = "daily_prices"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Security relationship
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id"), nullable=False)
    
    # Date and pricing data
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    
    # Volume and market data
    volume: Mapped[int] = mapped_column(Integer, default=0)
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    
    # Adjusted pricing (for splits and dividends)
    adjusted_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    split_factor: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=1.0)
    dividend_amount: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0.0)
    
    # Price change metrics
    price_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    price_change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Technical indicators (pre-calculated)
    sma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 20-day Simple Moving Average
    sma_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 50-day Simple Moving Average
    sma_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 200-day Simple Moving Average
    rsi_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))   # 14-day RSI
    
    # Data quality and source
    data_source: Mapped[str] = mapped_column(String(50), default="unknown")
    data_quality: Mapped[str] = mapped_column(String(20), default="good")  # good, fair, poor, estimated
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    security = relationship("Security", back_populates="daily_prices")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_daily_prices_security_date", "security_id", "price_date"),
        Index("idx_daily_prices_date", "price_date"),
        Index("idx_daily_prices_volume", "volume"),
        Index("idx_daily_prices_source", "data_source"),
        UniqueConstraint("security_id", "price_date", name="uq_security_daily_price"),
        CheckConstraint("open_price > 0", name="chk_daily_price_open_positive"),
        CheckConstraint("high_price >= low_price", name="chk_daily_price_high_low"),
        CheckConstraint("close_price > 0", name="chk_daily_price_close_positive"),
        CheckConstraint("volume >= 0", name="chk_daily_price_volume_positive"),
    )
    
    def __repr__(self):
        return f"<DailyPrice(security_id={self.security_id}, date={self.price_date}, close={self.close_price})>"


class IntradayPrice(BaseModel, TimestampMixin):
    """
    Intraday price data for real-time market tracking.
    
    Stores minute-level or tick-level price data for current market activity.
    """
    __tablename__ = "intraday_prices"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Security relationship
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id"), nullable=False)
    
    # Timestamp and pricing
    price_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    
    # Bid/Ask spread
    bid_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    ask_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    bid_size: Mapped[Optional[int]] = mapped_column(Integer)
    ask_size: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Market data
    is_market_hours: Mapped[bool] = mapped_column(Boolean, default=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Data source and quality
    data_source: Mapped[str] = mapped_column(String(50), default="unknown")
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)  # Data delay in minutes
    
    # Relationships
    security = relationship("Security", back_populates="intraday_prices")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_intraday_prices_security_timestamp", "security_id", "price_timestamp"),
        Index("idx_intraday_prices_timestamp", "price_timestamp"),
        Index("idx_intraday_prices_market_hours", "is_market_hours"),
        CheckConstraint("price > 0", name="chk_intraday_price_positive"),
        CheckConstraint("volume >= 0", name="chk_intraday_volume_positive"),
    )
    
    def __repr__(self):
        return f"<IntradayPrice(security_id={self.security_id}, timestamp={self.price_timestamp}, price={self.price})>"


class MarketIndex(BaseModel, TimestampMixin):
    """
    Market index data (S&P 500, Dow Jones, NASDAQ, etc.).
    
    Tracks major market indices for benchmarking and analysis.
    """
    __tablename__ = "market_indices"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Index identification
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Index metadata
    index_type: Mapped[str] = mapped_column(String(50), default="equity")  # equity, bond, commodity, crypto
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    country: Mapped[str] = mapped_column(String(2), default="US")
    
    # Current values
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    previous_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    change_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Index composition
    constituent_count: Mapped[Optional[int]] = mapped_column(Integer)
    total_market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    
    # Update tracking
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_provider: Mapped[str] = mapped_column(String(50), default="unknown")
    
    # Relationships
    index_history: Mapped[List["IndexHistory"]] = relationship("IndexHistory", back_populates="market_index", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_market_indices_symbol", "symbol"),
        Index("idx_market_indices_type", "index_type"),
        Index("idx_market_indices_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<MarketIndex(symbol='{self.symbol}', name='{self.name}', value={self.current_value})>"


class IndexHistory(BaseModel, TimestampMixin):
    """
    Historical data for market indices.
    
    Daily historical values for market indices used in performance comparison.
    """
    __tablename__ = "index_history"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Index relationship
    index_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_indices.id"), nullable=False)
    
    # Date and values
    history_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    high_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    low_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    close_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    
    # Performance metrics
    daily_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Relationships
    market_index = relationship("MarketIndex", back_populates="index_history")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_index_history_index_date", "index_id", "history_date"),
        Index("idx_index_history_date", "history_date"),
        UniqueConstraint("index_id", "history_date", name="uq_index_history_date"),
        CheckConstraint("close_value > 0", name="chk_index_close_positive"),
    )
    
    def __repr__(self):
        return f"<IndexHistory(index_id={self.index_id}, date={self.history_date}, close={self.close_value})>"


class EconomicIndicator(BaseModel, TimestampMixin):
    """
    Economic indicators and macroeconomic data.
    
    Tracks key economic metrics that may influence congressional trading decisions.
    """
    __tablename__ = "economic_indicators"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Indicator identification
    indicator_code: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Data point
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="percent")
    
    # Metadata
    category: Mapped[str] = mapped_column(String(100), default="economic")  # economic, monetary, employment, etc.
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")  # daily, weekly, monthly, quarterly, yearly
    data_source: Mapped[str] = mapped_column(String(100), default="unknown")
    is_preliminary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Change metrics
    previous_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6))
    value_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6))
    percent_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_economic_indicators_code_date", "indicator_code", "report_date"),
        Index("idx_economic_indicators_category", "category"),
        Index("idx_economic_indicators_date", "report_date"),
        UniqueConstraint("indicator_code", "report_date", name="uq_indicator_date"),
    )
    
    def __repr__(self):
        return f"<EconomicIndicator(code='{self.indicator_code}', date={self.report_date}, value={self.value})>"


class DataFeed(BaseModel, TimestampMixin):
    """
    Data feed configuration and monitoring.
    
    Tracks data sources, feed status, and data quality metrics.
    """
    __tablename__ = "data_feeds"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Feed identification
    feed_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    feed_type: Mapped[str] = mapped_column(String(50), nullable=False)  # price, index, economic, news
    
    # Configuration
    endpoint_url: Mapped[Optional[str]] = mapped_column(Text)
    api_key_required: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer)  # Requests per minute
    
    # Status and monitoring
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_successful_fetch: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Data quality metrics
    records_fetched_today: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100.0)
    avg_response_time: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))  # milliseconds
    
    # Configuration details
    fetch_frequency: Mapped[str] = mapped_column(String(50), default="daily")  # realtime, hourly, daily, etc.
    data_retention_days: Mapped[int] = mapped_column(Integer, default=365)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Indexes
    __table_args__ = (
        Index("idx_data_feeds_provider", "provider"),
        Index("idx_data_feeds_type", "feed_type"),
        Index("idx_data_feeds_active", "is_active"),
        Index("idx_data_feeds_healthy", "is_healthy"),
    )
    
    def __repr__(self):
        return f"<DataFeed(name='{self.feed_name}', provider='{self.provider}', active={self.is_active})>"


class MarketHoliday(BaseModel, TimestampMixin):
    """
    Market holidays and trading calendar.
    
    Tracks when markets are closed for holiday scheduling and data processing.
    """
    __tablename__ = "market_holidays"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Holiday details
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    holiday_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Market impact
    market: Mapped[str] = mapped_column(String(50), default="NYSE")  # NYSE, NASDAQ, BOND, etc.
    is_full_closure: Mapped[bool] = mapped_column(Boolean, default=True)
    early_close_time: Mapped[Optional[time]] = mapped_column(Time)  # If partial closure
    
    # Holiday metadata
    holiday_type: Mapped[str] = mapped_column(String(50), default="federal")  # federal, market, religious
    country: Mapped[str] = mapped_column(String(2), default="US")
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_market_holidays_date", "holiday_date"),
        Index("idx_market_holidays_market", "market"),
        Index("idx_market_holidays_type", "holiday_type"),
        UniqueConstraint("holiday_date", "market", name="uq_holiday_market_date"),
    )
    
    def __repr__(self):
        return f"<MarketHoliday(date={self.holiday_date}, name='{self.holiday_name}', market='{self.market}')>"


class TreasuryRate(BaseModel, TimestampMixin):
    """
    US Treasury rates and yield curve data.
    
    Tracks treasury yields for risk-free rate calculations and bond analysis.
    """
    __tablename__ = "treasury_rates"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Date and rates
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Treasury rates by maturity
    rate_1_month: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_3_month: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_6_month: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_1_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_2_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_3_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_5_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_7_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_10_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_20_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    rate_30_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    
    # Yield curve metrics
    spread_10y_2y: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))  # 10Y-2Y spread
    spread_10y_3m: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))  # 10Y-3M spread
    
    # Data source
    data_source: Mapped[str] = mapped_column(String(50), default="treasury.gov")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_treasury_rates_date", "rate_date"),
        UniqueConstraint("rate_date", name="uq_treasury_rate_date"),
    )
    
    def __repr__(self):
        return f"<TreasuryRate(date={self.rate_date}, 10y={self.rate_10_year})>" 