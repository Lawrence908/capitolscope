"""
Analytics domain package for CapitolScope.

This domain handles performance analysis, risk metrics calculations,
portfolio attribution, and advanced analytics reporting.
"""

from .models import (
    AnalyticsReport,
    PerformanceMetric,
    RiskMetric,
    BenchmarkComparison,
    SectorAnalysis,
    CorrelationMatrix
)

from .schemas import (
    AnalyticsReportCreate,
    AnalyticsReportResponse,
    PerformanceMetricResponse,
    RiskMetricResponse,
    BenchmarkComparisonResponse,
    SectorAnalysisResponse,
    AnalyticsQuery,
    RiskAnalysisRequest
)

from .services import AnalyticsService
from .crud import AnalyticsCRUD
from .interfaces import AnalyticsRepositoryProtocol, PerformanceCalculatorProtocol

__all__ = [
    # Models
    "AnalyticsReport",
    "PerformanceMetric",
    "RiskMetric",
    "BenchmarkComparison",
    "SectorAnalysis",
    "CorrelationMatrix",
    
    # Schemas
    "AnalyticsReportCreate",
    "AnalyticsReportResponse",
    "PerformanceMetricResponse",
    "RiskMetricResponse",
    "BenchmarkComparisonResponse",
    "SectorAnalysisResponse",
    "AnalyticsQuery",
    "RiskAnalysisRequest",
    
    # Services & CRUD
    "AnalyticsService",
    "AnalyticsCRUD",
    "AnalyticsRepositoryProtocol",
    "PerformanceCalculatorProtocol",
] 