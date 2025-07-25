"""
Health check schemas for the CapitolScope API.

This module contains Pydantic schemas for health check responses,
system status, and service monitoring.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import Field

from schemas.base import CapitolScopeBaseModel


# ============================================================================
# BASIC HEALTH CHECK SCHEMAS
# ============================================================================

class BasicHealthResponse(CapitolScopeBaseModel):
    """Basic health check response."""
    status: str = Field(..., description="Health status")
    timestamp: float = Field(..., description="Unix timestamp")
    environment: str = Field(..., description="Environment name")
    version: str = Field(..., description="API version")
    service: str = Field(..., description="Service name")


class LivenessResponse(CapitolScopeBaseModel):
    """Liveness check response."""
    status: str = Field(..., description="Liveness status")
    timestamp: float = Field(..., description="Unix timestamp")
    service: str = Field(..., description="Service name")


class ReadinessResponse(CapitolScopeBaseModel):
    """Readiness check response."""
    status: str = Field(..., description="Readiness status")
    timestamp: float = Field(..., description="Unix timestamp")


# ============================================================================
# DETAILED HEALTH CHECK SCHEMAS
# ============================================================================

class DatabaseHealth(CapitolScopeBaseModel):
    """Database health status."""
    status: str = Field(..., description="Database status")
    connection_ok: bool = Field(..., description="Connection status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Last health check")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")


class RedisHealth(CapitolScopeBaseModel):
    """Redis health status."""
    status: str = Field(..., description="Redis status")
    connection_ok: bool = Field(..., description="Connection status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")


class CongressAPIHealth(CapitolScopeBaseModel):
    """Congress.gov API health status."""
    status: str = Field(..., description="API status")
    api_key_configured: bool = Field(..., description="API key configured")
    connectivity: bool = Field(..., description="Connectivity status")
    authentication: bool = Field(..., description="Authentication status")
    data_availability: bool = Field(..., description="Data availability")
    last_successful_sync: Optional[str] = Field(None, description="Last successful sync")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    timestamp: Optional[float] = Field(None, description="Health check timestamp")


class ServiceChecks(CapitolScopeBaseModel):
    """Service health checks."""
    database: DatabaseHealth = Field(..., description="Database health")
    redis: RedisHealth = Field(..., description="Redis health")
    congress_api: CongressAPIHealth = Field(..., description="Congress API health")


class ConfigurationInfo(CapitolScopeBaseModel):
    """Configuration information."""
    debug: bool = Field(..., description="Debug mode enabled")
    environment: str = Field(..., description="Environment name")
    congress_api_configured: bool = Field(..., description="Congress API configured")


class DetailedHealthResponse(CapitolScopeBaseModel):
    """Detailed health check response."""
    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Unix timestamp")
    response_time_ms: float = Field(..., description="Health check response time")
    environment: str = Field(..., description="Environment name")
    version: str = Field(..., description="API version")
    service: str = Field(..., description="Service name")
    checks: ServiceChecks = Field(..., description="Service health checks")
    configuration: ConfigurationInfo = Field(..., description="Configuration information")


# ============================================================================
# SYSTEM STATUS SCHEMAS
# ============================================================================

class SystemMetrics(CapitolScopeBaseModel):
    """System metrics."""
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    disk_usage: Optional[float] = Field(None, description="Disk usage percentage")
    active_connections: Optional[int] = Field(None, description="Active database connections")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")


class PerformanceMetrics(CapitolScopeBaseModel):
    """Performance metrics."""
    average_response_time_ms: Optional[float] = Field(None, description="Average response time")
    requests_per_second: Optional[float] = Field(None, description="Requests per second")
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate")


class SystemStatusResponse(CapitolScopeBaseModel):
    """System status response."""
    status: str = Field(..., description="System status")
    timestamp: float = Field(..., description="Status timestamp")
    metrics: Optional[SystemMetrics] = Field(None, description="System metrics")
    performance: Optional[PerformanceMetrics] = Field(None, description="Performance metrics")
    warnings: List[str] = Field(default_factory=list, description="System warnings")
    errors: List[str] = Field(default_factory=list, description="System errors") 