"""
SQLAlchemy models for portfolio management.

This module defines the database models for tracking congressional member portfolios,
holdings, performance metrics, and historical snapshots.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, Boolean, 
    Text, ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

from domains.base.models import BaseModel, TimestampMixin


class Portfolio(BaseModel, TimestampMixin):
    """
    Portfolio entity representing a congress member's investment portfolio.
    
    A portfolio aggregates all holdings for a specific member and tracks
    overall performance metrics.
    """
    __tablename__ = "portfolios"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid.uuid4()), unique=True)
    
    # Portfolio ownership
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("congress_members.id"), nullable=False)
    portfolio_type: Mapped[str] = mapped_column(String(50), default="congressional")  # congressional, spouse, dependent
    
    # Portfolio metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Performance tracking
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_unrealized_gain: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_realized_gain: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    # Performance metrics
    ytd_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Year-to-date return %
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Total return %
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Risk metrics
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))  # Beta vs S&P 500
    volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Annualized volatility
    
    # Last update tracking
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_calculated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    member = relationship("CongressMember", back_populates="portfolios")
    holdings: Mapped[List["PortfolioHolding"]] = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    performance_history: Mapped[List["PortfolioPerformance"]] = relationship("PortfolioPerformance", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots: Mapped[List["PortfolioSnapshot"]] = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_portfolios_member_id", "member_id"),
        Index("idx_portfolios_type", "portfolio_type"),
        Index("idx_portfolios_active", "is_active"),
        Index("idx_portfolios_external_id", "external_id"),
        UniqueConstraint("member_id", "portfolio_type", name="uq_member_portfolio_type"),
    )
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, member_id={self.member_id}, name='{self.name}', value={self.total_value})>"


class PortfolioHolding(BaseModel, TimestampMixin):
    """
    Individual security holding within a portfolio.
    
    Tracks current position, cost basis, and performance for a specific security.
    """
    __tablename__ = "portfolio_holdings"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Relationships
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id"), nullable=False)
    
    # Position information
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)  # Shares/units held
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # Total cost basis
    average_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # Average cost per share
    
    # Current valuation
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    unrealized_gain: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    unrealized_gain_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Position metadata
    first_acquired: Mapped[date] = mapped_column(Date, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Tax tracking
    wash_sale_disallowed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    short_term_gain: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    long_term_gain: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    security = relationship("Security", back_populates="portfolio_holdings")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_holdings_portfolio_id", "portfolio_id"),
        Index("idx_holdings_security_id", "security_id"),
        Index("idx_holdings_active", "is_active"),
        Index("idx_holdings_first_acquired", "first_acquired"),
        UniqueConstraint("portfolio_id", "security_id", name="uq_portfolio_security"),
        CheckConstraint("quantity >= 0", name="chk_holdings_quantity_positive"),
        CheckConstraint("cost_basis >= 0", name="chk_holdings_cost_basis_positive"),
    )
    
    def __repr__(self):
        return f"<PortfolioHolding(id={self.id}, portfolio_id={self.portfolio_id}, security_id={self.security_id}, quantity={self.quantity})>"


class PortfolioPerformance(BaseModel, TimestampMixin):
    """
    Historical performance metrics for a portfolio over time.
    
    Stores daily/periodic performance snapshots for trend analysis.
    """
    __tablename__ = "portfolio_performance"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Relationships
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    
    # Time period
    performance_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), default="daily")  # daily, weekly, monthly, quarterly, yearly
    
    # Portfolio values
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cash_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    # Performance metrics
    total_return: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # Total gain/loss
    total_return_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # Total return %
    daily_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Daily return %
    
    # Benchmark comparison
    sp500_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    alpha: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Alpha vs S&P 500
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))  # Beta vs S&P 500
    
    # Risk metrics
    volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Rolling volatility
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Additional metrics
    number_of_holdings: Mapped[int] = mapped_column(Integer, default=0)
    largest_holding_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    sector_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="performance_history")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_performance_portfolio_id", "portfolio_id"),
        Index("idx_performance_date", "performance_date"),
        Index("idx_performance_period_type", "period_type"),
        Index("idx_performance_portfolio_date", "portfolio_id", "performance_date"),
        UniqueConstraint("portfolio_id", "performance_date", "period_type", name="uq_portfolio_performance_date"),
    )
    
    def __repr__(self):
        return f"<PortfolioPerformance(id={self.id}, portfolio_id={self.portfolio_id}, date={self.performance_date}, return={self.total_return_percent}%)>"


class PortfolioSnapshot(BaseModel, TimestampMixin):
    """
    Point-in-time snapshot of portfolio state.
    
    Captures complete portfolio state for historical analysis and reporting.
    """
    __tablename__ = "portfolio_snapshots"
    
    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Relationships
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    
    # Snapshot metadata
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled, triggered, manual
    trigger_event: Mapped[Optional[str]] = mapped_column(String(100))  # trade, rebalance, etc.
    
    # Portfolio state
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    number_of_positions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance at snapshot time
    total_return: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    total_return_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    ytd_return_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    
    # Risk metrics at snapshot time
    portfolio_beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))
    portfolio_volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    largest_position_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Sector allocation (top sectors)
    technology_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    healthcare_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    financial_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    energy_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    other_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Notes and metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    data_version: Mapped[str] = mapped_column(String(20), default="1.0")
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="snapshots")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_snapshots_portfolio_id", "portfolio_id"),
        Index("idx_snapshots_date", "snapshot_date"),
        Index("idx_snapshots_type", "snapshot_type"),
        Index("idx_snapshots_portfolio_date", "portfolio_id", "snapshot_date"),
    )
    
    def __repr__(self):
        return f"<PortfolioSnapshot(id={self.id}, portfolio_id={self.portfolio_id}, date={self.snapshot_date}, value={self.total_value})>" 