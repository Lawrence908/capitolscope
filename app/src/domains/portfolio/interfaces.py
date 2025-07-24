"""
Portfolio domain interfaces.

This module defines abstract interfaces for portfolio domain operations,
repositories, and services. Supports portfolio management, performance tracking,
and investment analytics.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from uuid import UUID

from domains.base.interfaces import (
    BaseRepository, BaseService, AnalyticsInterface
)
from domains.portfolio.schemas import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioDetailResponse,
    PortfolioHoldingCreate, PortfolioHoldingUpdate, PortfolioHoldingResponse,
    PortfolioPerformanceCreate, PortfolioPerformanceResponse,
    PortfolioSnapshotCreate, PortfolioSnapshotResponse,
    PortfolioSummary, PortfolioAnalyticsResponse, PortfolioComparisonResponse
)
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class PortfolioRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for portfolio repository operations."""
    
    @abstractmethod
    async def create(self, portfolio_data: PortfolioCreate) -> PortfolioDetailResponse:
        """Create a new portfolio."""
        pass
    
    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> Optional[PortfolioDetailResponse]:
        """Get portfolio by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[PortfolioSummary]:
        """Get all portfolios for a user."""
        pass
    
    @abstractmethod
    async def update(self, portfolio_id: UUID, update_data: PortfolioUpdate) -> Optional[PortfolioDetailResponse]:
        """Update portfolio."""
        pass
    
    @abstractmethod
    async def list_portfolios(self, user_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> Tuple[List[PortfolioSummary], int]:
        """List portfolios with pagination and filtering."""
        pass
    
    @abstractmethod
    async def delete(self, portfolio_id: UUID) -> bool:
        """Delete a portfolio."""
        pass
    
    @abstractmethod
    async def get_portfolio_holdings(self, portfolio_id: UUID) -> List[PortfolioHoldingResponse]:
        """Get all holdings for a portfolio."""
        pass
    
    @abstractmethod
    async def get_portfolio_performance(self, portfolio_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[PortfolioPerformanceResponse]:
        """Get performance history for a portfolio."""
        pass


class PortfolioHoldingRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for portfolio holding repository operations."""
    
    @abstractmethod
    async def create(self, holding_data: PortfolioHoldingCreate) -> PortfolioHoldingResponse:
        """Create a new portfolio holding."""
        pass
    
    @abstractmethod
    async def get_by_id(self, holding_id: UUID) -> Optional[PortfolioHoldingResponse]:
        """Get portfolio holding by ID."""
        pass
    
    @abstractmethod
    async def get_by_portfolio_and_security(self, portfolio_id: UUID, security_id: UUID) -> Optional[PortfolioHoldingResponse]:
        """Get specific holding for a portfolio and security."""
        pass
    
    @abstractmethod
    async def update(self, holding_id: UUID, update_data: PortfolioHoldingUpdate) -> Optional[PortfolioHoldingResponse]:
        """Update portfolio holding."""
        pass
    
    @abstractmethod
    async def list_holdings(self, portfolio_id: UUID, skip: int = 0, limit: int = 100) -> Tuple[List[PortfolioHoldingResponse], int]:
        """List holdings for a portfolio with pagination."""
        pass
    
    @abstractmethod
    async def delete(self, holding_id: UUID) -> bool:
        """Delete a portfolio holding."""
        pass
    
    @abstractmethod
    async def get_top_holdings(self, portfolio_id: UUID, limit: int = 10) -> List[PortfolioHoldingResponse]:
        """Get top holdings by value for a portfolio."""
        pass
    
    @abstractmethod
    async def get_sector_allocation(self, portfolio_id: UUID) -> Dict[str, Decimal]:
        """Get sector allocation for a portfolio."""
        pass


class PortfolioPerformanceRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for portfolio performance repository operations."""
    
    @abstractmethod
    async def create(self, performance_data: PortfolioPerformanceCreate) -> PortfolioPerformanceResponse:
        """Create a new performance record."""
        pass
    
    @abstractmethod
    async def get_by_id(self, performance_id: UUID) -> Optional[PortfolioPerformanceResponse]:
        """Get performance record by ID."""
        pass
    
    @abstractmethod
    async def get_by_portfolio_and_date(self, portfolio_id: UUID, date: date) -> Optional[PortfolioPerformanceResponse]:
        """Get performance record for a specific date."""
        pass
    
    @abstractmethod
    async def update(self, performance_id: UUID, update_data: Dict[str, Any]) -> Optional[PortfolioPerformanceResponse]:
        """Update performance record."""
        pass
    
    @abstractmethod
    async def list_performance(self, portfolio_id: UUID, start_date: date, end_date: date) -> List[PortfolioPerformanceResponse]:
        """Get performance history for a date range."""
        pass
    
    @abstractmethod
    async def get_latest_performance(self, portfolio_id: UUID) -> Optional[PortfolioPerformanceResponse]:
        """Get latest performance record for a portfolio."""
        pass
    
    @abstractmethod
    async def calculate_returns(self, portfolio_id: UUID, period_days: int) -> Optional[Dict[str, Decimal]]:
        """Calculate returns for a specific period."""
        pass
    
    @abstractmethod
    async def get_risk_metrics(self, portfolio_id: UUID, period_days: int = 252) -> Dict[str, Decimal]:
        """Calculate risk metrics for a portfolio."""
        pass


class PortfolioSnapshotRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for portfolio snapshot repository operations."""
    
    @abstractmethod
    async def create(self, snapshot_data: PortfolioSnapshotCreate) -> PortfolioSnapshotResponse:
        """Create a new portfolio snapshot."""
        pass
    
    @abstractmethod
    async def get_by_id(self, snapshot_id: UUID) -> Optional[PortfolioSnapshotResponse]:
        """Get portfolio snapshot by ID."""
        pass
    
    @abstractmethod
    async def get_by_portfolio_and_date(self, portfolio_id: UUID, date: date) -> Optional[PortfolioSnapshotResponse]:
        """Get snapshot for a specific date."""
        pass
    
    @abstractmethod
    async def update(self, snapshot_id: UUID, update_data: Dict[str, Any]) -> Optional[PortfolioSnapshotResponse]:
        """Update portfolio snapshot."""
        pass
    
    @abstractmethod
    async def list_snapshots(self, portfolio_id: UUID, start_date: date, end_date: date) -> List[PortfolioSnapshotResponse]:
        """Get snapshots for a date range."""
        pass
    
    @abstractmethod
    async def get_latest_snapshot(self, portfolio_id: UUID) -> Optional[PortfolioSnapshotResponse]:
        """Get latest snapshot for a portfolio."""
        pass


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class PortfolioServiceInterface(BaseService, ABC):
    """Abstract interface for portfolio business logic."""
    
    @abstractmethod
    async def create_portfolio(self, portfolio_data: PortfolioCreate, user_id: UUID) -> PortfolioDetailResponse:
        """Create a new portfolio with validation."""
        pass
    
    @abstractmethod
    async def update_portfolio(self, portfolio_id: UUID, update_data: PortfolioUpdate) -> PortfolioDetailResponse:
        """Update portfolio with business rules."""
        pass
    
    @abstractmethod
    async def get_portfolio_details(self, portfolio_id: UUID) -> PortfolioDetailResponse:
        """Get complete portfolio details with analytics."""
        pass
    
    @abstractmethod
    async def get_portfolio_analytics(self, portfolio_id: UUID) -> PortfolioAnalyticsResponse:
        """Get comprehensive analytics for a portfolio."""
        pass
    
    @abstractmethod
    async def add_holding(self, portfolio_id: UUID, holding_data: PortfolioHoldingCreate) -> PortfolioHoldingResponse:
        """Add a new holding to a portfolio."""
        pass
    
    @abstractmethod
    async def update_holding(self, holding_id: UUID, update_data: PortfolioHoldingUpdate) -> PortfolioHoldingResponse:
        """Update a portfolio holding."""
        pass
    
    @abstractmethod
    async def remove_holding(self, holding_id: UUID) -> bool:
        """Remove a holding from a portfolio."""
        pass
    
    @abstractmethod
    async def rebalance_portfolio(self, portfolio_id: UUID) -> bool:
        """Rebalance portfolio allocations."""
        pass
    
    @abstractmethod
    async def calculate_portfolio_value(self, portfolio_id: UUID) -> Decimal:
        """Calculate total portfolio value."""
        pass
    
    @abstractmethod
    async def compare_portfolios(self, portfolio_ids: List[UUID], benchmark: Optional[str] = None) -> PortfolioComparisonResponse:
        """Compare multiple portfolios."""
        pass


class PortfolioPerformanceServiceInterface(BaseService, ABC):
    """Abstract interface for portfolio performance business logic."""
    
    @abstractmethod
    async def record_daily_performance(self, portfolio_id: UUID, date: date) -> PortfolioPerformanceResponse:
        """Record daily portfolio performance."""
        pass
    
    @abstractmethod
    async def calculate_performance_metrics(self, portfolio_id: UUID, period_days: int) -> Dict[str, Decimal]:
        """Calculate performance metrics for a period."""
        pass
    
    @abstractmethod
    async def get_performance_history(self, portfolio_id: UUID, start_date: date, end_date: date) -> List[PortfolioPerformanceResponse]:
        """Get performance history for a date range."""
        pass
    
    @abstractmethod
    async def calculate_risk_metrics(self, portfolio_id: UUID, period_days: int = 252) -> Dict[str, Decimal]:
        """Calculate risk metrics for a portfolio."""
        pass
    
    @abstractmethod
    async def generate_performance_report(self, portfolio_id: UUID, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        pass


class PortfolioAnalyticsServiceInterface(BaseService, ABC):
    """Abstract interface for portfolio analytics business logic."""
    
    @abstractmethod
    async def analyze_portfolio_composition(self, portfolio_id: UUID) -> Dict[str, Any]:
        """Analyze portfolio composition and allocation."""
        pass
    
    @abstractmethod
    async def calculate_sector_allocation(self, portfolio_id: UUID) -> Dict[str, Decimal]:
        """Calculate sector allocation for a portfolio."""
        pass
    
    @abstractmethod
    async def analyze_risk_exposure(self, portfolio_id: UUID) -> Dict[str, Any]:
        """Analyze risk exposure and concentration."""
        pass
    
    @abstractmethod
    async def calculate_correlation_analysis(self, portfolio_id: UUID, benchmark: str = "SPY") -> Dict[str, Decimal]:
        """Calculate correlation with benchmark indices."""
        pass
    
    @abstractmethod
    async def generate_portfolio_insights(self, portfolio_id: UUID) -> Dict[str, Any]:
        """Generate insights and recommendations."""
        pass


# ============================================================================
# ANALYTICS INTERFACES
# ============================================================================

class PortfolioAnalyticsInterface(AnalyticsInterface, ABC):
    """Abstract interface for portfolio analytics."""
    
    @abstractmethod
    async def analyze_portfolio_performance(self, portfolio_id: UUID, period_days: int = 252) -> Dict[str, Any]:
        """Comprehensive performance analysis for a portfolio."""
        pass
    
    @abstractmethod
    async def get_portfolio_trends(self, user_id: UUID, period_days: int = 30) -> Dict[str, Any]:
        """Analyze portfolio trends across all user portfolios."""
        pass
    
    @abstractmethod
    async def detect_portfolio_anomalies(self, portfolio_id: UUID, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """Detect unusual portfolio activity."""
        pass
    
    @abstractmethod
    async def calculate_benchmark_comparison(self, portfolio_id: UUID, benchmark: str = "SPY") -> Dict[str, Decimal]:
        """Compare portfolio performance to benchmark."""
        pass
    
    @abstractmethod
    async def analyze_asset_allocation(self, portfolio_id: UUID) -> Dict[str, Decimal]:
        """Analyze asset allocation preferences."""
        pass
    
    @abstractmethod
    async def generate_portfolio_summary(self, portfolio_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate portfolio summary for a period."""
        pass
    
    @abstractmethod
    async def rank_portfolios_by_performance(self, user_id: UUID, period_days: int = 252) -> List[Dict[str, Any]]:
        """Rank portfolios by performance."""
        pass


# ============================================================================
# DATA PROCESSING INTERFACES
# ============================================================================

class PortfolioDataProcessorInterface(ABC):
    """Abstract interface for portfolio data processing."""
    
    @abstractmethod
    async def process_holding_data(self, raw_data: Dict[str, Any]) -> PortfolioHoldingCreate:
        """Process raw holding data into structured format."""
        pass
    
    @abstractmethod
    async def validate_portfolio_data(self, portfolio_data: PortfolioCreate) -> bool:
        """Validate portfolio data for consistency and completeness."""
        pass
    
    @abstractmethod
    async def enrich_portfolio_data(self, portfolio_id: UUID) -> PortfolioDetailResponse:
        """Enrich portfolio with market data and analytics."""
        pass
    
    @abstractmethod
    async def calculate_portfolio_metrics(self, portfolio_id: UUID) -> Dict[str, Decimal]:
        """Calculate various portfolio metrics."""
        pass


class PortfolioEnrichmentInterface(ABC):
    """Abstract interface for portfolio data enrichment."""
    
    @abstractmethod
    async def enrich_with_market_data(self, portfolio_id: UUID) -> bool:
        """Enrich portfolio with current market data."""
        pass
    
    @abstractmethod
    async def calculate_performance_metrics(self, portfolio_id: UUID) -> Dict[str, Decimal]:
        """Calculate performance metrics for a portfolio."""
        pass
    
    @abstractmethod
    async def update_portfolio_valuations(self, portfolio_id: UUID) -> bool:
        """Update portfolio valuations with current prices."""
        pass
    
    @abstractmethod
    async def link_to_securities(self, portfolio_id: UUID) -> bool:
        """Link portfolio holdings to securities in database."""
        pass


# ============================================================================
# NOTIFICATION INTERFACES
# ============================================================================

class PortfolioNotificationInterface(ABC):
    """Abstract interface for portfolio notifications."""
    
    @abstractmethod
    async def notify_portfolio_update(self, portfolio_id: UUID, changes: Dict[str, Any]) -> bool:
        """Send notification for portfolio updates."""
        pass
    
    @abstractmethod
    async def notify_performance_milestone(self, portfolio_id: UUID, milestone: str) -> bool:
        """Send notification for performance milestones."""
        pass
    
    @abstractmethod
    async def notify_rebalancing_alert(self, portfolio_id: UUID, allocation_changes: Dict[str, Any]) -> bool:
        """Send notification for rebalancing alerts."""
        pass
    
    @abstractmethod
    async def send_portfolio_summary(self, user_id: UUID, period: str = "daily") -> bool:
        """Send periodic portfolio summary."""
        pass


# Log interface creation
logger.info("Portfolio domain interfaces initialized")

# Export all interfaces
__all__ = [
    # Repository interfaces
    "PortfolioRepositoryInterface",
    "PortfolioHoldingRepositoryInterface", 
    "PortfolioPerformanceRepositoryInterface",
    "PortfolioSnapshotRepositoryInterface",
    
    # Service interfaces
    "PortfolioServiceInterface",
    "PortfolioPerformanceServiceInterface",
    "PortfolioAnalyticsServiceInterface",
    
    # Analytics interfaces
    "PortfolioAnalyticsInterface",
    
    # Data processing interfaces
    "PortfolioDataProcessorInterface",
    "PortfolioEnrichmentInterface",
    
    # Notification interfaces
    "PortfolioNotificationInterface"
] 