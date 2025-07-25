"""
Portfolio domain package for CapitolScope.

This domain handles portfolio management, performance calculations,
holdings tracking, and investment analytics.
"""

from .models import (
    Portfolio,
    PortfolioHolding,
    PortfolioPerformance,
    PortfolioSnapshot
)

from .schemas import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    PortfolioHoldingResponse,
    PortfolioPerformanceResponse,
    PortfolioSnapshotResponse
)

from .services import PortfolioService
from .crud import PortfolioCRUD
from .interfaces import PortfolioRepositoryInterface

__all__ = [
    # Models
    "Portfolio",
    "PortfolioHolding", 
    "PortfolioPerformance",
    "PortfolioSnapshot",
    
    # Schemas
    "PortfolioCreate",
    "PortfolioUpdate",
    "PortfolioResponse",
    "PortfolioHoldingResponse",
    "PortfolioPerformanceResponse",
    "PortfolioSnapshotResponse",
    
    # Services & CRUD
    "PortfolioService",
    "PortfolioCRUD",
    "PortfolioRepositoryInterface",
] 