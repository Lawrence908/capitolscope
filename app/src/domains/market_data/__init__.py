"""
Market Data domain package for CapitolScope.

This domain handles real-time and historical market data including
stock prices, market indices, economic indicators, and data feeds.
"""

from .models import (
    DailyPrice,
    IntradayPrice,
    MarketIndex,
    EconomicIndicator,
    DataFeed,
    MarketHoliday
)

from .schemas import (
    DailyPriceCreate,
    DailyPriceResponse,
    IntradayPriceResponse,
    MarketIndexResponse,
    EconomicIndicatorResponse,
    PriceQueryParams,
    MarketDataRequest
)

from .services import MarketDataService
from .crud import MarketDataCRUD
from .interfaces import MarketDataRepositoryProtocol, PriceDataProviderProtocol

__all__ = [
    # Models
    "DailyPrice",
    "IntradayPrice",
    "MarketIndex",
    "EconomicIndicator", 
    "DataFeed",
    "MarketHoliday",
    
    # Schemas
    "DailyPriceCreate",
    "DailyPriceResponse",
    "IntradayPriceResponse",
    "MarketIndexResponse",
    "EconomicIndicatorResponse",
    "PriceQueryParams",
    "MarketDataRequest",
    
    # Services & CRUD
    "MarketDataService",
    "MarketDataCRUD",
    "MarketDataRepositoryProtocol",
    "PriceDataProviderProtocol",
] 