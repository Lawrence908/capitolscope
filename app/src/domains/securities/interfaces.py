"""
Securities domain interfaces and protocols.

This module defines abstract interfaces and protocols specific to the securities domain,
supporting CAP-24 (Stock Database) and CAP-25 (Price Data Ingestion).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable
from datetime import date, datetime

from domains.base.interfaces import DataIngestionInterface, ExternalAPIInterface
from domains.securities.schemas import (
    SecurityCreate, SecurityUpdate, SecurityResponse, SecuritySummary,
    DailyPriceCreate, PriceHistory, BulkOperationResponse
)
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# PRICE DATA INTERFACES
# ============================================================================

@runtime_checkable
class PriceDataProvider(Protocol):
    """Protocol for price data providers."""
    
    def get_current_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current price for a ticker."""
        ...
    
    def get_historical_prices(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get historical price data."""
        ...
    
    def get_intraday_prices(self, ticker: str, interval: str = "1min") -> List[Dict[str, Any]]:
        """Get intraday price data."""
        ...


class PriceDataIngestionInterface(DataIngestionInterface):
    """Abstract interface for price data ingestion."""
    
    @abstractmethod
    def ingest_daily_prices(self, prices: List[DailyPriceCreate]) -> BulkOperationResponse:
        """Ingest daily price data."""
        pass
    
    @abstractmethod
    def ingest_from_provider(self, provider: PriceDataProvider, tickers: List[str]) -> Dict[str, Any]:
        """Ingest price data from external provider."""
        pass
    
    @abstractmethod
    def schedule_price_update(self, ticker: str, frequency: str = "daily") -> bool:
        """Schedule automatic price updates."""
        pass


# ============================================================================
# SECURITY LOOKUP INTERFACES
# ============================================================================

@runtime_checkable
class SecurityLookupProvider(Protocol):
    """Protocol for security lookup providers."""
    
    def lookup_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Look up security by ticker."""
        ...
    
    def lookup_by_isin(self, isin: str) -> Optional[Dict[str, Any]]:
        """Look up security by ISIN."""
        ...
    
    def lookup_by_cusip(self, cusip: str) -> Optional[Dict[str, Any]]:
        """Look up security by CUSIP."""
        ...
    
    def search_securities(self, query: str) -> List[Dict[str, Any]]:
        """Search for securities."""
        ...


class SecurityEnrichmentInterface(ABC):
    """Abstract interface for security data enrichment."""
    
    @abstractmethod
    def enrich_security_data(self, security: SecurityResponse) -> SecurityResponse:
        """Enrich security with additional data."""
        pass
    
    @abstractmethod
    def calculate_technical_indicators(self, security_id: int) -> Dict[str, float]:
        """Calculate technical indicators."""
        pass
    
    @abstractmethod
    def get_fundamental_data(self, security_id: int) -> Dict[str, Any]:
        """Get fundamental analysis data."""
        pass


# ============================================================================
# MARKET DATA INTERFACES
# ============================================================================

@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol for market data providers."""
    
    def get_market_status(self, exchange: str) -> Dict[str, Any]:
        """Get market status for an exchange."""
        ...
    
    def get_market_movers(self, market: str = "US") -> Dict[str, List[Dict[str, Any]]]:
        """Get market movers (gainers, losers, most active)."""
        ...
    
    def get_sector_performance(self) -> List[Dict[str, Any]]:
        """Get sector performance data."""
        ...
    
    def get_market_indices(self) -> List[Dict[str, Any]]:
        """Get market indices data."""
        ...


class MarketDataInterface(ABC):
    """Abstract interface for market data operations."""
    
    @abstractmethod
    def get_real_time_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote."""
        pass
    
    @abstractmethod
    def get_market_snapshot(self) -> Dict[str, Any]:
        """Get market snapshot."""
        pass
    
    @abstractmethod
    def get_top_gainers(self, limit: int = 10) -> List[SecuritySummary]:
        """Get top gaining securities."""
        pass
    
    @abstractmethod
    def get_top_losers(self, limit: int = 10) -> List[SecuritySummary]:
        """Get top losing securities."""
        pass
    
    @abstractmethod
    def get_most_active(self, limit: int = 10) -> List[SecuritySummary]:
        """Get most active securities."""
        pass


# ============================================================================
# CORPORATE ACTIONS INTERFACES
# ============================================================================

@runtime_checkable
class CorporateActionProvider(Protocol):
    """Protocol for corporate action data providers."""
    
    def get_upcoming_dividends(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming dividend payments."""
        ...
    
    def get_upcoming_splits(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming stock splits."""
        ...
    
    def get_earnings_calendar(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get earnings calendar."""
        ...


class CorporateActionInterface(ABC):
    """Abstract interface for corporate action operations."""
    
    @abstractmethod
    def process_dividend(self, security_id: int, dividend_data: Dict[str, Any]) -> bool:
        """Process dividend payment."""
        pass
    
    @abstractmethod
    def process_split(self, security_id: int, split_data: Dict[str, Any]) -> bool:
        """Process stock split."""
        pass
    
    @abstractmethod
    def adjust_prices_for_split(self, security_id: int, split_ratio: float, split_date: date) -> bool:
        """Adjust historical prices for stock split."""
        pass


# ============================================================================
# PORTFOLIO TRACKING INTERFACES
# ============================================================================

@runtime_checkable
class PortfolioTracker(Protocol):
    """Protocol for portfolio tracking."""
    
    def track_position(self, user_id: str, security_id: int, quantity: float) -> bool:
        """Track a portfolio position."""
        ...
    
    def calculate_portfolio_value(self, user_id: str) -> Dict[str, Any]:
        """Calculate portfolio value."""
        ...
    
    def get_portfolio_performance(self, user_id: str, period: str = "1y") -> Dict[str, Any]:
        """Get portfolio performance."""
        ...


class PortfolioInterface(ABC):
    """Abstract interface for portfolio operations."""
    
    @abstractmethod
    def create_portfolio(self, user_id: str, name: str) -> Dict[str, Any]:
        """Create a new portfolio."""
        pass
    
    @abstractmethod
    def add_position(self, portfolio_id: int, security_id: int, quantity: float, cost_basis: float) -> bool:
        """Add position to portfolio."""
        pass
    
    @abstractmethod
    def calculate_returns(self, portfolio_id: int, start_date: date, end_date: date) -> Dict[str, float]:
        """Calculate portfolio returns."""
        pass


# ============================================================================
# WATCHLIST INTERFACES
# ============================================================================

@runtime_checkable
class WatchlistProvider(Protocol):
    """Protocol for watchlist providers."""
    
    def get_user_watchlist(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's watchlist."""
        ...
    
    def add_to_watchlist(self, user_id: str, security_id: int) -> bool:
        """Add security to watchlist."""
        ...
    
    def remove_from_watchlist(self, user_id: str, security_id: int) -> bool:
        """Remove security from watchlist."""
        ...


class WatchlistInterface(ABC):
    """Abstract interface for watchlist operations."""
    
    @abstractmethod
    def create_watchlist(self, user_id: str, name: str) -> Dict[str, Any]:
        """Create a new watchlist."""
        pass
    
    @abstractmethod
    def set_price_alert(self, user_id: str, security_id: int, target_price: float, alert_type: str) -> bool:
        """Set price alert."""
        pass
    
    @abstractmethod
    def check_price_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Check triggered price alerts."""
        pass


# ============================================================================
# ANALYTICS INTERFACES
# ============================================================================

@runtime_checkable
class SecurityAnalytics(Protocol):
    """Protocol for security analytics."""
    
    def calculate_volatility(self, security_id: int, period: int = 30) -> float:
        """Calculate price volatility."""
        ...
    
    def calculate_beta(self, security_id: int, benchmark_id: int) -> float:
        """Calculate beta vs benchmark."""
        ...
    
    def calculate_correlation(self, security_id1: int, security_id2: int) -> float:
        """Calculate correlation between securities."""
        ...


class SecurityAnalyticsInterface(ABC):
    """Abstract interface for security analytics."""
    
    @abstractmethod
    def generate_price_chart(self, security_id: int, period: str = "1y") -> Dict[str, Any]:
        """Generate price chart data."""
        pass
    
    @abstractmethod
    def calculate_technical_indicators(self, security_id: int) -> Dict[str, float]:
        """Calculate technical indicators."""
        pass
    
    @abstractmethod
    def generate_performance_report(self, security_id: int) -> Dict[str, Any]:
        """Generate performance report."""
        pass


# ============================================================================
# EXTERNAL API INTERFACES
# ============================================================================

class AlphaVantageInterface(ExternalAPIInterface):
    """Interface for Alpha Vantage API integration."""
    
    @abstractmethod
    def get_daily_prices(self, ticker: str) -> Dict[str, Any]:
        """Get daily prices from Alpha Vantage."""
        pass
    
    @abstractmethod
    def get_company_overview(self, ticker: str) -> Dict[str, Any]:
        """Get company overview."""
        pass


class PolygonInterface(ExternalAPIInterface):
    """Interface for Polygon.io API integration."""
    
    @abstractmethod
    def get_aggregates(self, ticker: str, timespan: str, from_date: date, to_date: date) -> Dict[str, Any]:
        """Get price aggregates."""
        pass
    
    @abstractmethod
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get ticker details."""
        pass


class YahooFinanceInterface(ExternalAPIInterface):
    """Interface for Yahoo Finance API integration."""
    
    @abstractmethod
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get quote data."""
        pass
    
    @abstractmethod
    def get_historical_data(self, ticker: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get historical data."""
        pass


# ============================================================================
# CACHING INTERFACES
# ============================================================================

@runtime_checkable
class PriceCache(Protocol):
    """Protocol for price data caching."""
    
    def cache_price(self, ticker: str, price_data: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache price data."""
        ...
    
    def get_cached_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get cached price data."""
        ...
    
    def invalidate_price_cache(self, ticker: str) -> bool:
        """Invalidate price cache."""
        ...


class PriceCacheInterface(ABC):
    """Abstract interface for price caching."""
    
    @abstractmethod
    def cache_real_time_quote(self, ticker: str, quote: Dict[str, Any]) -> bool:
        """Cache real-time quote."""
        pass
    
    @abstractmethod
    def cache_historical_prices(self, ticker: str, prices: List[Dict[str, Any]]) -> bool:
        """Cache historical prices."""
        pass
    
    @abstractmethod
    def get_cached_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get cached quote."""
        pass


# ============================================================================
# VALIDATION INTERFACES
# ============================================================================

class SecurityValidationInterface(ABC):
    """Abstract interface for security validation."""
    
    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker symbol."""
        pass
    
    @abstractmethod
    def validate_isin(self, isin: str) -> bool:
        """Validate ISIN."""
        pass
    
    @abstractmethod
    def validate_cusip(self, cusip: str) -> bool:
        """Validate CUSIP."""
        pass
    
    @abstractmethod
    def validate_price_data(self, price_data: Dict[str, Any]) -> bool:
        """Validate price data."""
        pass


class PriceValidationInterface(ABC):
    """Abstract interface for price validation."""
    
    @abstractmethod
    def validate_price_range(self, price: float, historical_prices: List[float]) -> bool:
        """Validate price is within reasonable range."""
        pass
    
    @abstractmethod
    def detect_price_anomalies(self, prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect price anomalies."""
        pass
    
    @abstractmethod
    def validate_ohlc_data(self, ohlc: Dict[str, float]) -> bool:
        """Validate OHLC data consistency."""
        pass


# Log interface initialization
logger.info("Securities domain interfaces initialized")

# Export all interfaces
__all__ = [
    "PriceDataProvider",
    "PriceDataIngestionInterface",
    "SecurityLookupProvider",
    "SecurityEnrichmentInterface",
    "MarketDataProvider",
    "MarketDataInterface",
    "CorporateActionProvider",
    "CorporateActionInterface",
    "PortfolioTracker",
    "PortfolioInterface",
    "WatchlistProvider",
    "WatchlistInterface",
    "SecurityAnalytics",
    "SecurityAnalyticsInterface",
    "AlphaVantageInterface",
    "PolygonInterface",
    "YahooFinanceInterface",
    "PriceCache",
    "PriceCacheInterface",
    "SecurityValidationInterface",
    "PriceValidationInterface"
] 