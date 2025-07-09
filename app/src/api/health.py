"""
Health check endpoints for monitoring and Docker health checks.
"""

from typing import Dict, Any
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

from core.database import check_database_health
from core.config import settings
from core.responses import success_response, error_response

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def health_check() -> JSONResponse:
    """
    Basic health check endpoint.
    
    Returns application status and basic system information.
    """
    data = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "service": "capitolscope-api"
    }
    
    return success_response(data=data)


@router.get("/detailed")
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check with database and external service status.
    
    Returns comprehensive health information for monitoring systems.
    """
    start_time = time.time()
    
    # Check database health
    database_health = await check_database_health()
    
    # Check Redis health (if configured)
    redis_health = {"status": "not_configured"}
    # TODO: Add Redis health check when implemented
    
    # Calculate response time
    response_time = (time.time() - start_time) * 1000
    
    # Determine overall status
    overall_status = "healthy"
    if database_health["status"] != "healthy":
        overall_status = "degraded"
    
    data = {
        "status": overall_status,
        "timestamp": time.time(),
        "response_time_ms": round(response_time, 2),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "service": "capitolscope-api",
        "checks": {
            "database": database_health,
            "redis": redis_health,
        },
        "configuration": {
            "debug": settings.DEBUG,
            "environment": settings.ENVIRONMENT,
        }
    }
    
    # Return success or error based on overall status
    if overall_status == "healthy":
        return success_response(data=data)
    else:
        return error_response(
            message="System degraded - check service health",
            error_code="system_degraded",
            status_code=503
        )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical dependencies
    database_health = await check_database_health()
    
    if database_health["status"] != "healthy":
        logger.warning("Readiness check failed", reason="database_unhealthy")
        
        return error_response(
            message="Service not ready - database connection failed",
            error_code="not_ready",
            status_code=503,
            details={
                "reason": "database_connection_failed",
                "timestamp": time.time()
            }
        )
    
    data = {
        "status": "ready",
        "timestamp": time.time()
    }
    
    return success_response(data=data)


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the service is alive and should not be restarted.
    """
    data = {
        "status": "alive",
        "timestamp": time.time(),
        "service": "capitolscope-api"
    }
    
    return success_response(data=data) 