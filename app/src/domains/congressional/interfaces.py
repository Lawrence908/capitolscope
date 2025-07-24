"""
Congressional domain interfaces.

This module defines abstract interfaces for congressional domain operations,
repositories, and services. Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from uuid import UUID

from domains.base.interfaces import (
    BaseRepository, BaseService, AnalyticsInterface
)
from domains.congressional.schemas import (
    CongressMemberCreate, CongressMemberUpdate, CongressMemberDetail, CongressMemberSummary,
    CongressionalTradeCreate, CongressionalTradeUpdate, CongressionalTradeDetail, CongressionalTradeSummary,
    CongressionalTradeQuery, MemberQuery, CongressionalTradeFilter,
    MemberPortfolioSummary, PortfolioPerformanceSummary,
    TradingStatistics, MemberAnalytics, MarketPerformanceComparison
)
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class CongressMemberRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for congress member repository operations."""
    
    @abstractmethod
    async def create(self, member_data: CongressMemberCreate) -> CongressMemberDetail:
        """Create a new congress member."""
        pass
    
    @abstractmethod
    async def get_by_id(self, member_id: UUID) -> Optional[CongressMemberDetail]:
        """Get congress member by ID."""
        pass
    
    @abstractmethod
    async def get_by_bioguide_id(self, bioguide_id: str) -> Optional[CongressMemberDetail]:
        """Get congress member by bioguide ID."""
        pass
    
    @abstractmethod
    async def update(self, member_id: UUID, update_data: CongressMemberUpdate) -> Optional[CongressMemberDetail]:
        """Update congress member."""
        pass
    
    @abstractmethod
    async def list_members(self, query: MemberQuery) -> Tuple[List[CongressMemberSummary], int]:
        """List congress members with pagination and filtering."""
        pass
    
    @abstractmethod
    async def search_members(self, search_term: str, limit: int = 10) -> List[CongressMemberSummary]:
        """Search congress members by name."""
        pass
    
    @abstractmethod
    async def get_members_by_state(self, state: str) -> List[CongressMemberSummary]:
        """Get all members from a specific state."""
        pass
    
    @abstractmethod
    async def get_active_members(self) -> List[CongressMemberSummary]:
        """Get all currently active members."""
        pass
    
    @abstractmethod
    async def get_trading_statistics(self, member_id: int) -> TradingStatistics:
        """Get trading statistics for a member."""
        pass


class CongressionalTradeRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for congressional trade repository operations."""
    
    @abstractmethod
    async def create(self, trade_data: CongressionalTradeCreate) -> CongressionalTradeDetail:
        """Create a new congressional trade."""
        pass
    
    @abstractmethod
    async def get_by_id(self, trade_id: int) -> Optional[CongressionalTradeDetail]:
        """Get congressional trade by ID."""
        pass
    
    @abstractmethod
    async def update(self, trade_id: int, update_data: CongressionalTradeUpdate) -> Optional[CongressionalTradeDetail]:
        """Update congressional trade."""
        pass
    
    @abstractmethod
    async def list_trades(self, query: CongressionalTradeQuery) -> Tuple[List[CongressionalTradeSummary], int]:
        """List congressional trades with pagination and filtering."""
        pass
    
    @abstractmethod
    async def get_member_trades(self, member_id: int, limit: Optional[int] = None) -> List[CongressionalTradeSummary]:
        """Get all trades for a specific member."""
        pass
    
    @abstractmethod
    async def get_trades_by_ticker(self, ticker: str, limit: Optional[int] = None) -> List[CongressionalTradeSummary]:
        """Get all trades for a specific ticker."""
        pass
    
    @abstractmethod
    async def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[CongressionalTradeSummary]:
        """Get trades within a date range."""
        pass
    
    @abstractmethod
    async def get_recent_trades(self, days: int = 30, limit: int = 100) -> List[CongressionalTradeSummary]:
        """Get recent trades within specified days."""
        pass
    
    @abstractmethod
    async def get_large_trades(self, min_amount: int, limit: int = 100) -> List[CongressionalTradeSummary]:
        """Get trades above a minimum amount threshold."""
        pass
    
    @abstractmethod
    async def bulk_create(self, trades_data: List[CongressionalTradeCreate]) -> List[CongressionalTradeDetail]:
        """Bulk create congressional trades."""
        pass
    
    @abstractmethod
    async def update_price_performance(self, trade_id: int, price_changes: Dict[str, Decimal]) -> bool:
        """Update price performance data for a trade."""
        pass


class MemberPortfolioRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for member portfolio repository operations."""
    
    @abstractmethod
    async def get_member_portfolio(self, member_id: int) -> List[MemberPortfolioSummary]:
        """Get current portfolio for a member."""
        pass
    
    @abstractmethod
    async def get_member_position(self, member_id: int, security_id: int) -> Optional[MemberPortfolioSummary]:
        """Get specific position for a member."""
        pass
    
    @abstractmethod
    async def update_position(self, member_id: int, security_id: int, transaction_data: Dict[str, Any]) -> MemberPortfolioSummary:
        """Update portfolio position based on a trade."""
        pass
    
    @abstractmethod
    async def calculate_portfolio_value(self, member_id: int) -> int:
        """Calculate total portfolio value for a member."""
        pass
    
    @abstractmethod
    async def get_top_positions(self, member_id: int, limit: int = 10) -> List[MemberPortfolioSummary]:
        """Get top positions by value for a member."""
        pass
    
    @abstractmethod
    async def get_sector_allocation(self, member_id: int) -> Dict[str, Decimal]:
        """Get sector allocation for a member's portfolio."""
        pass


class PortfolioPerformanceRepositoryInterface(BaseRepository, ABC):
    """Abstract interface for portfolio performance repository operations."""
    
    @abstractmethod
    async def record_daily_performance(self, member_id: int, date: date, performance_data: Dict[str, Any]) -> PortfolioPerformanceSummary:
        """Record daily portfolio performance."""
        pass
    
    @abstractmethod
    async def get_performance_history(self, member_id: int, start_date: date, end_date: date) -> List[PortfolioPerformanceSummary]:
        """Get performance history for a date range."""
        pass
    
    @abstractmethod
    async def get_latest_performance(self, member_id: int) -> Optional[PortfolioPerformanceSummary]:
        """Get latest performance record for a member."""
        pass
    
    @abstractmethod
    async def calculate_returns(self, member_id: int, period_days: int) -> Optional[MarketPerformanceComparison]:
        """Calculate returns for a specific period."""
        pass
    
    @abstractmethod
    async def get_risk_metrics(self, member_id: int, period_days: int = 252) -> Dict[str, Decimal]:
        """Calculate risk metrics for a member's portfolio."""
        pass


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class CongressMemberServiceInterface(BaseService, ABC):
    """Abstract interface for congress member business logic."""
    
    @abstractmethod
    async def create_member(self, member_data: CongressMemberCreate) -> CongressMemberDetail:
        """Create a new congress member with validation."""
        pass
    
    @abstractmethod
    async def update_member(self, member_id: int, update_data: CongressMemberUpdate) -> CongressMemberDetail:
        """Update congress member with business rules."""
        pass
    
    @abstractmethod
    async def get_member_profile(self, member_id: int) -> CongressMemberDetail:
        """Get complete member profile with analytics."""
        pass
    
    @abstractmethod
    async def get_member_analytics(self, member_id: int) -> MemberAnalytics:
        """Get comprehensive analytics for a member."""
        pass
    
    @abstractmethod
    async def sync_member_data(self, bioguide_id: str) -> CongressMemberDetail:
        """Sync member data from external sources."""
        pass
    
    @abstractmethod
    async def calculate_influence_score(self, member_id: int) -> Decimal:
        """Calculate influence score based on various factors."""
        pass
    
    @abstractmethod
    async def get_similar_members(self, member_id: int, limit: int = 5) -> List[CongressMemberSummary]:
        """Find members with similar trading patterns."""
        pass


class CongressionalTradeServiceInterface(BaseService, ABC):
    """Abstract interface for congressional trade business logic."""
    
    @abstractmethod
    async def process_trade_filing(self, filing_data: Dict[str, Any]) -> List[CongressionalTradeDetail]:
        """Process raw trade filing data into structured trades."""
        pass
    
    @abstractmethod
    async def validate_trade_data(self, trade_data: CongressionalTradeCreate) -> bool:
        """Validate trade data for consistency and completeness."""
        pass
    
    @abstractmethod
    async def enrich_trade_data(self, trade_id: int) -> CongressionalTradeDetail:
        """Enrich trade with security information and market data."""
        pass
    
    @abstractmethod
    async def detect_duplicate_trades(self, trade_data: CongressionalTradeCreate) -> List[CongressionalTradeDetail]:
        """Detect potential duplicate trades."""
        pass
    
    @abstractmethod
    async def calculate_trade_performance(self, trade_id: int) -> Dict[str, Decimal]:
        """Calculate performance metrics for a trade."""
        pass
    
    @abstractmethod
    async def analyze_trading_patterns(self, member_id: int) -> Dict[str, Any]:
        """Analyze trading patterns for a member."""
        pass
    
    @abstractmethod
    async def get_trade_insights(self, filters: CongressionalTradeFilter) -> Dict[str, Any]:
        """Get insights from filtered trade data."""
        pass


class PortfolioServiceInterface(BaseService, ABC):
    """Abstract interface for portfolio management business logic."""
    
    @abstractmethod
    async def update_member_portfolio(self, trade: CongressionalTradeDetail) -> List[MemberPortfolioSummary]:
        """Update member portfolio based on a new trade."""
        pass
    
    @abstractmethod
    async def calculate_daily_performance(self, member_id: int, date: date) -> PortfolioPerformanceSummary:
        """Calculate and record daily portfolio performance."""
        pass
    
    @abstractmethod
    async def rebalance_portfolio_allocations(self, member_id: int) -> bool:
        """Recalculate portfolio allocations and percentages."""
        pass
    
    @abstractmethod
    async def generate_portfolio_report(self, member_id: int, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate comprehensive portfolio report."""
        pass
    
    @abstractmethod
    async def compare_portfolio_performance(self, member_id: int, benchmark: str, period_days: int) -> MarketPerformanceComparison:
        """Compare portfolio performance to benchmark."""
        pass
    
    @abstractmethod
    async def calculate_risk_metrics(self, member_id: int) -> Dict[str, Decimal]:
        """Calculate portfolio risk metrics."""
        pass


# ============================================================================
# ANALYTICS INTERFACES
# ============================================================================

class CongressionalAnalyticsInterface(AnalyticsInterface, ABC):
    """Abstract interface for congressional trading analytics."""
    
    @abstractmethod
    async def analyze_member_performance(self, member_id: int, period_days: int = 252) -> MemberAnalytics:
        """Comprehensive performance analysis for a member."""
        pass
    
    @abstractmethod
    async def get_trading_trends(self, period_days: int = 30) -> Dict[str, Any]:
        """Analyze overall trading trends across all members."""
        pass
    
    @abstractmethod
    async def detect_unusual_activity(self, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """Detect unusual trading activity."""
        pass
    
    @abstractmethod
    async def calculate_market_correlation(self, member_id: int, market_index: str = "SPY") -> Decimal:
        """Calculate correlation with market indices."""
        pass
    
    @abstractmethod
    async def analyze_sector_preferences(self, member_id: int) -> Dict[str, Decimal]:
        """Analyze sector investment preferences."""
        pass
    
    @abstractmethod
    async def generate_trading_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate trading summary for a period."""
        pass
    
    @abstractmethod
    async def rank_members_by_performance(self, period_days: int = 252, limit: int = 50) -> List[Dict[str, Any]]:
        """Rank members by portfolio performance."""
        pass
    
    @abstractmethod
    async def analyze_disclosure_timing(self, member_id: Optional[int] = None) -> Dict[str, Any]:
        """Analyze trade disclosure timing patterns."""
        pass


# ============================================================================
# DATA PROCESSING INTERFACES
# ============================================================================

class TradeDataProcessorInterface(ABC):
    """Abstract interface for trade data processing."""
    
    @abstractmethod
    async def parse_trade_document(self, document_url: str) -> List[Dict[str, Any]]:
        """Parse trade disclosure document."""
        pass
    
    @abstractmethod
    async def match_security(self, asset_description: str) -> Optional[Dict[str, Any]]:
        """Match asset description to security in database."""
        pass
    
    @abstractmethod
    async def extract_ticker_symbol(self, asset_description: str) -> Optional[str]:
        """Extract ticker symbol from asset description."""
        pass
    
    @abstractmethod
    async def parse_trade_amount(self, amount_text: str) -> Dict[str, Optional[int]]:
        """Parse trade amount from text."""
        pass
    
    @abstractmethod
    async def validate_member_identification(self, member_data: Dict[str, Any]) -> bool:
        """Validate member identification data."""
        pass


class TradeEnrichmentInterface(ABC):
    """Abstract interface for trade data enrichment."""
    
    @abstractmethod
    async def enrich_with_market_data(self, trade_id: int) -> bool:
        """Enrich trade with market data at time of transaction."""
        pass
    
    @abstractmethod
    async def calculate_performance_metrics(self, trade_id: int) -> Dict[str, Decimal]:
        """Calculate performance metrics for a trade."""
        pass
    
    @abstractmethod
    async def update_trade_confidence_scores(self, trade_id: int) -> bool:
        """Update confidence scores for parsed trade data."""
        pass
    
    @abstractmethod
    async def link_to_security(self, trade_id: int, security_id: int) -> bool:
        """Link trade to security in database."""
        pass


# ============================================================================
# NOTIFICATION INTERFACES
# ============================================================================

class TradeNotificationInterface(ABC):
    """Abstract interface for trade notifications."""
    
    @abstractmethod
    async def notify_new_trade(self, trade: CongressionalTradeDetail) -> bool:
        """Send notification for new trade."""
        pass
    
    @abstractmethod
    async def notify_large_trade(self, trade: CongressionalTradeDetail, threshold: int) -> bool:
        """Send notification for large trade."""
        pass
    
    @abstractmethod
    async def notify_unusual_activity(self, member_id: int, activity_data: Dict[str, Any]) -> bool:
        """Send notification for unusual trading activity."""
        pass
    
    @abstractmethod
    async def send_daily_summary(self, recipient_list: List[str]) -> bool:
        """Send daily trading summary."""
        pass


# Log interface creation
logger.info("Congressional domain interfaces initialized")

# Export all interfaces
__all__ = [
    # Repository interfaces
    "CongressMemberRepositoryInterface",
    "CongressionalTradeRepositoryInterface", 
    "MemberPortfolioRepositoryInterface",
    "PortfolioPerformanceRepositoryInterface",
    
    # Service interfaces
    "CongressMemberServiceInterface",
    "CongressionalTradeServiceInterface",
    "PortfolioServiceInterface",
    
    # Analytics interfaces
    "CongressionalAnalyticsInterface",
    
    # Data processing interfaces
    "TradeDataProcessorInterface",
    "TradeEnrichmentInterface",
    
    # Notification interfaces
    "TradeNotificationInterface"
] 