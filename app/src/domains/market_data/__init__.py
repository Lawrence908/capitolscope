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

# Schemas/services/crud are partially built; import them best-effort so the
# always-valid model exports above are never blocked by an unfinished symbol.
try:  # pragma: no cover - optional exports
    from .schemas import (
        DailyPriceResponse,
        IntradayPriceResponse,
        MarketIndexResponse,
        EconomicIndicatorResponse,
    )
except Exception:  # noqa: BLE001
    pass

__all__ = [
    "DailyPrice",
    "IntradayPrice",
    "MarketIndex",
    "EconomicIndicator",
    "DataFeed",
    "MarketHoliday",
] 