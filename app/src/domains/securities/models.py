"""
Securities domain database models.

This module contains SQLAlchemy models for securities, asset types, exchanges,
and price data. Supports CAP-24 (Stock Database) and CAP-25 (Price Data Ingestion).
"""

import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, 
    BigInteger, ForeignKey, CheckConstraint,
    UniqueConstraint, Index
)
from sqlalchemy.types import Numeric as SQLDecimal
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from domains.base.models import CapitolScopeBaseModel, ActiveRecordMixin, MetadataMixin, TimestampMixin
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# ASSET TYPES
# ============================================================================

class AssetType(CapitolScopeBaseModel, ActiveRecordMixin):
    """Asset type model for categorizing securities."""
    
    __tablename__ = 'asset_types'
    
    code = Column(String(5), primary_key=True, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # equity, bond, derivative, etc.
    risk_level = Column(Integer)  # 1-5 scale
    
    # Relationships
    securities = relationship("Security", back_populates="asset_type", foreign_keys="Security.asset_type_code")
    
    def __repr__(self):
        return f"<AssetType(code={self.code}, name={self.name})>"


# ============================================================================
# SECTORS
# ============================================================================

class Sector(CapitolScopeBaseModel, ActiveRecordMixin):
    """Sector model for categorizing securities by industry."""
    
    __tablename__ = 'sectors'
    
    gics_code = Column(String(10), primary_key=True, unique=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    parent_sector_gics_code = Column(String(10), ForeignKey('sectors.gics_code'))
    market_sensitivity = Column(SQLDecimal(5, 4))  # Beta-like measure
    volatility_score = Column(SQLDecimal(5, 4))  # Historical volatility
    
    # Relationships
    securities = relationship("Security", back_populates="sector", foreign_keys="Security.sector_gics_code")
    parent_sector = relationship("Sector", remote_side="Sector.gics_code")
    
    def __repr__(self):
        return f"<Sector(name={self.name}, gics_code={self.gics_code})>"


# ============================================================================
# EXCHANGES
# ============================================================================

class Exchange(CapitolScopeBaseModel, ActiveRecordMixin):
    """Exchange model for trading venues."""
    
    __tablename__ = 'exchanges'
    
    code = Column(String(10), primary_key=True, unique=True, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(3), nullable=False)  # ISO 3166-1 alpha-3
    timezone = Column(String(50), nullable=False)
    trading_hours = Column(JSONB)  # Trading hours configuration
    market_cap_rank = Column(Integer)  # Global ranking
    
    # Relationships
    securities = relationship("Security", back_populates="exchange", foreign_keys="Security.exchange_code")
    
    def __repr__(self):
        return f"<Exchange(code={self.code}, name={self.name})>"


# ============================================================================
# SECURITIES
# ============================================================================

class Security(CapitolScopeBaseModel, ActiveRecordMixin, MetadataMixin, TimestampMixin):
    """Security model for stocks, bonds, ETFs, and other financial instruments."""
    
    __tablename__ = 'securities'
    
    # Basic information
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    
    # Foreign keys
    asset_type_code = Column(String(5), ForeignKey('asset_types.code'), index=True)
    sector_gics_code = Column(String(10), ForeignKey('sectors.gics_code'), index=True)
    exchange_code = Column(String(10), ForeignKey('exchanges.code'), index=True)
    
    # Financial data
    currency = Column(String(3), default='USD')
    market_cap = Column(BigInteger)  # in cents
    shares_outstanding = Column(BigInteger)
    
    # Identifiers
    isin = Column(String(12), unique=True, index=True)  # International Securities Identification Number
    cusip = Column(String(9), unique=True, index=True)  # Committee on Uniform Securities Identification Procedures
    figi = Column(String(12), unique=True, index=True)  # Financial Instrument Global Identifier
    
    # ML Features for analysis
    beta = Column(SQLDecimal(8, 6))  # Market beta
    pe_ratio = Column(SQLDecimal(8, 2))  # Price-to-earnings ratio
    dividend_yield = Column(SQLDecimal(8, 6))  # Annual dividend yield
    volatility_30d = Column(SQLDecimal(8, 6))  # 30-day volatility
    volume_avg_30d = Column(BigInteger)  # 30-day average volume
    
    # ESG and Social Impact
    esg_score = Column(SQLDecimal(5, 2))  # ESG score (0-100)
    controversy_score = Column(SQLDecimal(5, 2))  # Controversy score
    
    # Relationships
    asset_type = relationship("AssetType", back_populates="securities", foreign_keys=[asset_type_code])
    sector = relationship("Sector", back_populates="securities", foreign_keys=[sector_gics_code])
    exchange = relationship("Exchange", back_populates="securities", foreign_keys=[exchange_code])
    daily_prices = relationship("DailyPrice", back_populates="security")
    corporate_actions = relationship("CorporateAction", back_populates="security")
    portfolio_holdings = relationship("PortfolioHolding", back_populates="security")
    member_portfolios = relationship("MemberPortfolio", back_populates="security")
    congressional_trades = relationship("CongressionalTrade", back_populates="security")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('ticker', 'exchange_code', name='unique_ticker_exchange'),
        Index('idx_security_ticker', 'ticker'),
        Index('idx_security_name', 'name'),
        Index('idx_security_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Security(ticker={self.ticker}, name={self.name})>"
    
    @property
    def display_name(self) -> str:
        """Return a formatted display name."""
        return f"{self.ticker} - {self.name}"
    
    def get_market_cap_formatted(self) -> str:
        """Return formatted market cap string."""
        if not self.market_cap:
            return "N/A"
        
        market_cap_dollars = self.market_cap / 100
        if market_cap_dollars >= 1_000_000_000:
            return f"${market_cap_dollars / 1_000_000_000:.1f}B"
        elif market_cap_dollars >= 1_000_000:
            return f"${market_cap_dollars / 1_000_000:.1f}M"
        else:
            return f"${market_cap_dollars:,.0f}"


# ============================================================================
# PRICE DATA
# ============================================================================

class DailyPrice(CapitolScopeBaseModel, TimestampMixin):
    """Daily price data for securities."""
    
    __tablename__ = 'daily_prices'
    
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), nullable=False, index=True)
    price_date = Column(Date, nullable=False, index=True)
    
    # OHLCV data (all prices in cents)
    open_price = Column(Integer, nullable=False)
    high_price = Column(Integer, nullable=False)
    low_price = Column(Integer, nullable=False)
    close_price = Column(Integer, nullable=False)
    adjusted_close = Column(Integer)  # Split/dividend adjusted
    volume = Column(BigInteger, nullable=False)
    
    # Technical indicators (optional, calculated)
    rsi_14 = Column(SQLDecimal(5, 2))  # 14-day RSI
    macd = Column(SQLDecimal(10, 6))  # MACD value
    bollinger_upper = Column(Integer)  # Bollinger upper band (cents)
    bollinger_lower = Column(Integer)  # Bollinger lower band (cents)
    
    # Relationships
    security = relationship("Security", back_populates="daily_prices")
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('security_id', 'price_date', name='unique_security_date'),
        Index('idx_daily_price_security_date', 'security_id', 'price_date'),
        Index('idx_daily_price_date', 'price_date'),
        # Check constraints for price validity
        CheckConstraint('open_price >= 0', name='check_open_price_positive'),
        CheckConstraint('high_price >= 0', name='check_high_price_positive'),
        CheckConstraint('low_price >= 0', name='check_low_price_positive'),
        CheckConstraint('close_price >= 0', name='check_close_price_positive'),
        CheckConstraint('volume >= 0', name='check_volume_positive'),
        CheckConstraint('high_price >= low_price', name='check_high_ge_low'),
    )
    
    def __repr__(self):
        return f"<DailyPrice(security_id={self.security_id}, date={self.price_date}, close={self.close_price})>"
    
    @property
    def price_change(self) -> Optional[int]:
        """Calculate price change from open to close."""
        if self.open_price and self.close_price:
            return self.close_price - self.open_price
        return None
    
    @property
    def price_change_percent(self) -> Optional[float]:
        """Calculate percentage price change."""
        if self.open_price and self.close_price and self.open_price > 0:
            return ((self.close_price - self.open_price) / self.open_price) * 100
        return None
    
    def get_price_formatted(self, price_type: str = "close") -> str:
        """Return formatted price string."""
        price_map = {
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "adjusted": self.adjusted_close
        }
        
        price = price_map.get(price_type, self.close_price)
        if price:
            return f"${price / 100:.2f}"
        return "N/A"


# ============================================================================
# CORPORATE ACTIONS
# ============================================================================

class CorporateAction(CapitolScopeBaseModel, TimestampMixin):
    """Corporate actions affecting securities (splits, dividends, etc.)."""
    
    __tablename__ = 'corporate_actions'
    
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), nullable=False, index=True)
    action_type = Column(String(20), nullable=False, index=True)
    
    # Important dates
    ex_date = Column(Date, nullable=False, index=True)  # Ex-dividend/ex-rights date
    record_date = Column(Date, index=True)  # Record date
    payment_date = Column(Date, index=True)  # Payment date
    
    # Action details
    ratio = Column(SQLDecimal(10, 6))  # For splits (e.g., 2.0 for 2:1 split)
    amount = Column(Integer)  # Dividend amount in cents
    description = Column(Text)
    
    # Impact tracking
    price_impact_1d = Column(SQLDecimal(8, 6))  # 1-day price impact
    volume_impact_1d = Column(SQLDecimal(8, 6))  # 1-day volume impact
    
    # Relationships
    security = relationship("Security", back_populates="corporate_actions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            action_type.in_(['split', 'dividend', 'spinoff', 'merger', 'rights_offering']), 
            name='check_action_type'
        ),
        CheckConstraint('amount >= 0', name='check_amount_positive'),
        CheckConstraint('ratio > 0', name='check_ratio_positive'),
        Index('idx_corporate_action_security_date', 'security_id', 'ex_date'),
        Index('idx_corporate_action_type', 'action_type'),
    )
    
    def __repr__(self):
        return f"<CorporateAction(security_id={self.security_id}, type={self.action_type}, ex_date={self.ex_date})>"
    
    def get_formatted_amount(self) -> str:
        """Return formatted dividend amount."""
        if self.amount:
            return f"${self.amount / 100:.2f}"
        return "N/A"
    
    def get_formatted_ratio(self) -> str:
        """Return formatted split ratio."""
        if self.ratio:
            return f"{self.ratio}:1"
        return "N/A"


# ============================================================================
# PRICE HISTORY AGGREGATES (For performance)
# ============================================================================

class PriceHistoryAggregate(CapitolScopeBaseModel, TimestampMixin):
    """Pre-calculated price history aggregates for performance."""
    
    __tablename__ = 'price_history_aggregates'
    
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)  # 'weekly', 'monthly', 'quarterly', 'yearly'
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Aggregated OHLCV data
    open_price = Column(Integer, nullable=False)
    high_price = Column(Integer, nullable=False)
    low_price = Column(Integer, nullable=False)
    close_price = Column(Integer, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    # Performance metrics
    total_return = Column(SQLDecimal(10, 6))  # Total return for period
    volatility = Column(SQLDecimal(8, 6))  # Price volatility
    
    # Relationships
    security = relationship("Security")
    
    __table_args__ = (
        UniqueConstraint('security_id', 'period_type', 'period_start', name='unique_security_period'),
        Index('idx_price_aggregate_security_period', 'security_id', 'period_type'),
        CheckConstraint(
            period_type.in_(['weekly', 'monthly', 'quarterly', 'yearly']), 
            name='check_period_type'
        ),
    )
    
    def __repr__(self):
        return f"<PriceHistoryAggregate(security_id={self.security_id}, period={self.period_type})>"


# ============================================================================
# WATCHLISTS (User-specific)
# ============================================================================

class SecurityWatchlist(CapitolScopeBaseModel, TimestampMixin):
    """User watchlists for tracking securities."""
    
    __tablename__ = 'security_watchlists'
    
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # UUID as string
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), nullable=False, index=True)
    
    # Watchlist metadata
    notes = Column(Text)
    alert_price_target = Column(Integer)  # Price target in cents
    alert_enabled = Column(Boolean, default=False)
    
    # Relationships
    security = relationship("Security")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'security_id', name='unique_user_security'),
        Index('idx_watchlist_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<SecurityWatchlist(user_id={self.user_id}, security_id={self.security_id})>"


# --- Fix for circular import: Import PortfolioHolding and assign relationship after both classes are defined ---
from domains.portfolio.models import PortfolioHolding

Security.portfolio_holdings = relationship("PortfolioHolding", back_populates="security")

# Log model creation
logger.info("Securities domain models initialized")

# Export all models
__all__ = [
    "AssetType",
    "Sector", 
    "Exchange",
    "Security",
    "DailyPrice",
    "CorporateAction",
    "PriceHistoryAggregate",
    "SecurityWatchlist"
] 