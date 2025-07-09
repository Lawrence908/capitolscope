"""
Trading domain package for CapitolScope.

This domain handles trade analysis, transaction patterns, correlation analysis,
and trading behavior insights for congressional members.
"""

from .models import (
    TradeAnalysis,
    TradingPattern,
    TradeCorrelation,
    TransactionCluster,
    TradingBehavior,
    MarketTiming
)

from .schemas import (
    TradeAnalysisCreate,
    TradeAnalysisResponse,
    TradingPatternResponse,
    TradeCorrelationResponse,
    TransactionClusterResponse,
    TradingBehaviorResponse,
    TradeAnalysisQuery,
    PatternAnalysisRequest
)

from .services import TradingAnalysisService
from .crud import TradingAnalysisCRUD
from .interfaces import TradingAnalysisRepositoryProtocol, PatternDetectionProtocol

__all__ = [
    # Models
    "TradeAnalysis",
    "TradingPattern",
    "TradeCorrelation",
    "TransactionCluster",
    "TradingBehavior",
    "MarketTiming",
    
    # Schemas
    "TradeAnalysisCreate",
    "TradeAnalysisResponse",
    "TradingPatternResponse",
    "TradeCorrelationResponse",
    "TransactionClusterResponse",
    "TradingBehaviorResponse",
    "TradeAnalysisQuery",
    "PatternAnalysisRequest",
    
    # Services & CRUD
    "TradingAnalysisService",
    "TradingAnalysisCRUD",
    "TradingAnalysisRepositoryProtocol",
    "PatternDetectionProtocol",
] 