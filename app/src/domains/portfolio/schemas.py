"""
Pydantic schemas for portfolio domain.

This module defines the request/response schemas for portfolio management,
including validation and serialization for API endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator
from pydantic.types import PositiveInt, NonNegativeInt

from schemas.base import BaseResponse, PaginatedResponse


# ============================================================================
# Portfolio Schemas
# ============================================================================

class PortfolioBase(BaseModel):
    """Base schema for portfolio data."""
    name: str = Field(..., min_length=1, max_length=255, description="Portfolio name")
    description: Optional[str] = Field(None, max_length=1000, description="Portfolio description")
    portfolio_type: str = Field("congressional", description="Portfolio type (congressional, spouse, dependent)")
    is_active: bool = Field(True, description="Whether portfolio is active")


class PortfolioCreate(PortfolioBase):
    """Schema for creating a new portfolio."""
    member_id: PositiveInt = Field(..., description="Congress member ID")
    
    @field_validator("portfolio_type")
    @classmethod
    def validate_portfolio_type(cls, v):
        valid_types = ["congressional", "spouse", "dependent", "joint"]
        if v not in valid_types:
            raise ValueError(f"Portfolio type must be one of: {valid_types}")
        return v


class PortfolioUpdate(BaseModel):
    """Schema for updating an existing portfolio."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class PortfolioResponse(PortfolioBase, BaseResponse):
    """Schema for portfolio response data."""
    id: int
    external_id: str
    member_id: int
    
    # Performance tracking
    total_value: Decimal = Field(default=0, description="Total portfolio value")
    total_cost_basis: Decimal = Field(default=0, description="Total cost basis")
    total_unrealized_gain: Decimal = Field(default=0, description="Total unrealized gain/loss")
    total_realized_gain: Decimal = Field(default=0, description="Total realized gain/loss")
    
    # Performance metrics
    ytd_return: Optional[Decimal] = Field(None, description="Year-to-date return percentage")
    total_return: Optional[Decimal] = Field(None, description="Total return percentage")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    
    # Risk metrics
    beta: Optional[Decimal] = Field(None, description="Beta vs S&P 500")
    volatility: Optional[Decimal] = Field(None, description="Annualized volatility")
    
    # Metadata
    last_updated: datetime
    last_calculated: Optional[datetime]
    
    # Holdings summary
    holdings_count: Optional[int] = Field(None, description="Number of holdings")
    
    @computed_field
    @property
    def total_return_percent(self) -> Optional[Decimal]:
        """Calculate total return percentage."""
        if self.total_cost_basis and self.total_cost_basis > 0:
            return (self.total_unrealized_gain + self.total_realized_gain) / self.total_cost_basis * 100
        return None
    
    model_config = ConfigDict(from_attributes=True)


class PortfolioSummary(BaseModel):
    """Summary schema for portfolio listings."""
    id: int
    external_id: str
    member_id: int
    name: str
    portfolio_type: str
    total_value: Decimal
    total_return_percent: Optional[Decimal]
    holdings_count: int
    last_updated: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Portfolio Holding Schemas
# ============================================================================

class PortfolioHoldingBase(BaseModel):
    """Base schema for portfolio holding data."""
    quantity: Decimal = Field(..., gt=0, description="Number of shares/units held")
    cost_basis: Decimal = Field(..., ge=0, description="Total cost basis")
    average_cost: Decimal = Field(..., gt=0, description="Average cost per share")


class PortfolioHoldingCreate(PortfolioHoldingBase):
    """Schema for creating a new portfolio holding."""
    portfolio_id: PositiveInt = Field(..., description="Portfolio ID")
    security_id: PositiveInt = Field(..., description="Security ID")
    first_acquired: date = Field(..., description="Date first acquired")


class PortfolioHoldingUpdate(BaseModel):
    """Schema for updating portfolio holding."""
    quantity: Optional[Decimal] = Field(None, gt=0)
    cost_basis: Optional[Decimal] = Field(None, ge=0)
    average_cost: Optional[Decimal] = Field(None, gt=0)
    current_price: Optional[Decimal] = Field(None, gt=0)


class PortfolioHoldingResponse(PortfolioHoldingBase, BaseResponse):
    """Schema for portfolio holding response data."""
    id: int
    portfolio_id: int
    security_id: int
    
    # Current valuation
    current_price: Optional[Decimal] = Field(None, description="Current price per share")
    current_value: Optional[Decimal] = Field(None, description="Current total value")
    unrealized_gain: Optional[Decimal] = Field(None, description="Unrealized gain/loss")
    unrealized_gain_percent: Optional[Decimal] = Field(None, description="Unrealized gain/loss percentage")
    
    # Position metadata
    first_acquired: date
    last_updated: datetime
    is_active: bool
    
    # Tax tracking
    wash_sale_disallowed: Decimal = Field(default=0)
    short_term_gain: Decimal = Field(default=0)
    long_term_gain: Decimal = Field(default=0)
    
    # Security information (if joined)
    security_symbol: Optional[str] = None
    security_name: Optional[str] = None
    security_type: Optional[str] = None
    
    @computed_field
    @property
    def allocation_percent(self) -> Optional[Decimal]:
        """Calculate position allocation percentage (requires portfolio context)."""
        # This would be calculated at the service layer with portfolio total value
        return None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Portfolio Performance Schemas
# ============================================================================

class PortfolioPerformanceBase(BaseModel):
    """Base schema for portfolio performance data."""
    performance_date: date = Field(..., description="Performance date")
    period_type: str = Field("daily", description="Period type (daily, weekly, monthly, etc.)")
    total_value: Decimal = Field(..., ge=0, description="Total portfolio value")
    total_cost_basis: Decimal = Field(..., ge=0, description="Total cost basis")


class PortfolioPerformanceCreate(PortfolioPerformanceBase):
    """Schema for creating portfolio performance record."""
    portfolio_id: PositiveInt = Field(..., description="Portfolio ID")
    
    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, v):
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if v not in valid_periods:
            raise ValueError(f"Period type must be one of: {valid_periods}")
        return v


class PortfolioPerformanceResponse(PortfolioPerformanceBase, BaseResponse):
    """Schema for portfolio performance response data."""
    id: int
    portfolio_id: int
    
    cash_value: Decimal = Field(default=0)
    
    # Performance metrics
    total_return: Decimal = Field(description="Total gain/loss")
    total_return_percent: Decimal = Field(description="Total return percentage")
    daily_return: Optional[Decimal] = Field(None, description="Daily return percentage")
    
    # Benchmark comparison
    sp500_return: Optional[Decimal] = Field(None, description="S&P 500 return for same period")
    alpha: Optional[Decimal] = Field(None, description="Alpha vs S&P 500")
    beta: Optional[Decimal] = Field(None, description="Beta vs S&P 500")
    
    # Risk metrics
    volatility: Optional[Decimal] = Field(None, description="Portfolio volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    
    # Portfolio composition
    number_of_holdings: int = Field(default=0)
    largest_holding_percent: Optional[Decimal] = Field(None)
    sector_concentration: Optional[Decimal] = Field(None)
    
    model_config = ConfigDict(from_attributes=True)


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics schema."""
    total_return_percent: Decimal
    annualized_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    best_month: Optional[Decimal] = None
    worst_month: Optional[Decimal] = None


# ============================================================================
# Portfolio Snapshot Schemas
# ============================================================================

class PortfolioSnapshotBase(BaseModel):
    """Base schema for portfolio snapshot data."""
    snapshot_date: datetime = Field(..., description="Snapshot timestamp")
    snapshot_type: str = Field("scheduled", description="Snapshot type")
    trigger_event: Optional[str] = Field(None, description="Event that triggered snapshot")
    total_value: Decimal = Field(..., ge=0, description="Total portfolio value")
    total_cost_basis: Decimal = Field(..., ge=0, description="Total cost basis")


class PortfolioSnapshotCreate(PortfolioSnapshotBase):
    """Schema for creating portfolio snapshot."""
    portfolio_id: PositiveInt = Field(..., description="Portfolio ID")
    
    @field_validator("snapshot_type")
    @classmethod
    def validate_snapshot_type(cls, v):
        valid_types = ["scheduled", "triggered", "manual", "trade", "rebalance"]
        if v not in valid_types:
            raise ValueError(f"Snapshot type must be one of: {valid_types}")
        return v


class PortfolioSnapshotResponse(PortfolioSnapshotBase, BaseResponse):
    """Schema for portfolio snapshot response data."""
    id: int
    portfolio_id: int
    
    cash_balance: Decimal = Field(default=0)
    number_of_positions: int = Field(default=0)
    
    # Performance at snapshot time
    total_return: Decimal
    total_return_percent: Decimal
    ytd_return_percent: Optional[Decimal] = None
    
    # Risk metrics at snapshot time
    portfolio_beta: Optional[Decimal] = None
    portfolio_volatility: Optional[Decimal] = None
    largest_position_percent: Optional[Decimal] = None
    
    # Sector allocation
    technology_percent: Optional[Decimal] = None
    healthcare_percent: Optional[Decimal] = None
    financial_percent: Optional[Decimal] = None
    energy_percent: Optional[Decimal] = None
    other_percent: Optional[Decimal] = None
    
    notes: Optional[str] = None
    data_version: str = Field(default="1.0")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Complex Response Schemas
# ============================================================================

class PortfolioDetailResponse(PortfolioResponse):
    """Detailed portfolio response with holdings and performance."""
    holdings: List[PortfolioHoldingResponse] = Field(default_factory=list)
    recent_performance: List[PortfolioPerformanceResponse] = Field(default_factory=list)
    performance_metrics: Optional[PerformanceMetrics] = None
    sector_allocation: Dict[str, Decimal] = Field(default_factory=dict)
    top_holdings: List[PortfolioHoldingResponse] = Field(default_factory=list)


class PortfolioComparisonResponse(BaseModel):
    """Schema for comparing multiple portfolios."""
    portfolios: List[PortfolioSummary]
    comparison_metrics: Dict[str, Any]
    benchmark_performance: Dict[str, Decimal]
    correlation_matrix: Dict[str, Dict[str, Decimal]]
    
    model_config = ConfigDict(from_attributes=True)


class PortfolioAnalyticsResponse(BaseModel):
    """Advanced analytics response for portfolio."""
    portfolio_id: int
    analysis_date: datetime
    
    # Performance analysis
    performance_metrics: PerformanceMetrics
    risk_metrics: Dict[str, Decimal]
    
    # Attribution analysis
    sector_attribution: Dict[str, Decimal]
    security_attribution: List[Dict[str, Any]]
    
    # Risk analysis
    var_95: Optional[Decimal] = None  # Value at Risk
    expected_shortfall: Optional[Decimal] = None
    beta_exposure: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Recommendations
    rebalancing_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    risk_warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Paginated Response Schemas
# ============================================================================

class PortfolioPaginatedResponse(PaginatedResponse[PortfolioSummary]):
    """Paginated response for portfolio listings."""
    pass


class PortfolioHoldingPaginatedResponse(PaginatedResponse[PortfolioHoldingResponse]):
    """Paginated response for portfolio holdings."""
    pass


class PortfolioPerformancePaginatedResponse(PaginatedResponse[PortfolioPerformanceResponse]):
    """Paginated response for portfolio performance data."""
    pass


# ============================================================================
# Filter and Query Schemas
# ============================================================================

class PortfolioFilter(BaseModel):
    """Filter criteria for portfolio queries."""
    member_id: Optional[int] = None
    portfolio_type: Optional[str] = None
    is_active: Optional[bool] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class PortfolioSort(BaseModel):
    """Sort criteria for portfolio queries."""
    field: str = Field("last_updated", description="Field to sort by")
    direction: str = Field("desc", description="Sort direction (asc/desc)")
    
    @field_validator("field")
    @classmethod
    def validate_sort_field(cls, v):
        valid_fields = [
            "name", "total_value", "total_return_percent", "last_updated",
            "created_at", "member_id", "portfolio_type"
        ]
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {valid_fields}")
        return v
    
    @field_validator("direction")
    @classmethod
    def validate_sort_direction(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("Sort direction must be 'asc' or 'desc'")
        return v.lower()


class PerformanceQuery(BaseModel):
    """Query parameters for performance analysis."""
    date_from: date = Field(..., description="Start date for analysis")
    date_to: date = Field(..., description="End date for analysis")
    period_type: str = Field("daily", description="Period type for aggregation")
    benchmark: str = Field("SPY", description="Benchmark symbol for comparison")
    include_risk_metrics: bool = Field(True, description="Include risk metrics calculation")
    
    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, v):
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if v not in valid_periods:
            raise ValueError(f"Period type must be one of: {valid_periods}")
        return v 