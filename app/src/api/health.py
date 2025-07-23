#!/usr/bin/env python3
"""
Health check endpoints for monitoring and Docker health checks.
"""

from typing import Dict, Any
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

from core.database import check_database_health, DatabaseManager
from core.config import settings
from core.responses import success_response, error_response
from schemas.base import ResponseEnvelope, create_response

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Health check successful"},
        500: {"description": "Health check failed"}
    }
)
async def health_check() -> ResponseEnvelope[Dict[str, Any]]:
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
    
    return create_response(data=data)


@router.get(
    "/detailed",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Detailed health check successful"},
        503: {"description": "System degraded"},
        500: {"description": "Health check failed"}
    }
)
async def detailed_health_check() -> ResponseEnvelope[Dict[str, Any]]:
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
    
    # Check Congress.gov API health
    congress_api_health = await check_congress_api_health()
    
    # Calculate response time
    response_time = (time.time() - start_time) * 1000
    
    # Determine overall status
    overall_status = "healthy"
    if database_health["status"] != "healthy":
        overall_status = "degraded"
    if congress_api_health["status"] != "healthy":
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
            "congress_api": congress_api_health,
        },
        "configuration": {
            "debug": settings.DEBUG,
            "environment": settings.ENVIRONMENT,
            "congress_api_configured": bool(settings.CONGRESS_GOV_API_KEY),
        }
    }
    
    # Return success or error based on overall status
    if overall_status == "healthy":
        return create_response(data=data)
    else:
        return create_response(error="System degraded - check service health")


@router.get(
    "/congress-api",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Congress API health check successful"},
        503: {"description": "Congress API unhealthy"},
        500: {"description": "Health check failed"}
    }
)
async def congress_api_health_check() -> ResponseEnvelope[Dict[str, Any]]:
    """
    Specific health check for Congress.gov API integration.
    
    Tests API connectivity, authentication, and data availability.
    """
    start_time = time.time()
    
    health_data = await check_congress_api_health()
    response_time = (time.time() - start_time) * 1000
    
    health_data["response_time_ms"] = round(response_time, 2)
    health_data["timestamp"] = time.time()
    
    if health_data["status"] == "healthy":
        return create_response(data=health_data)
    else:
        return create_response(error="Congress.gov API health check failed")


@router.get(
    "/ready",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Service ready"},
        503: {"description": "Service not ready"}
    }
)
async def readiness_check() -> ResponseEnvelope[Dict[str, Any]]:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical dependencies
    database_health = await check_database_health()
    
    if database_health["status"] != "healthy":
        logger.warning("Readiness check failed", reason="database_unhealthy")
        
        return create_response(error="Service not ready - database connection failed")
    
    data = {
        "status": "ready",
        "timestamp": time.time()
    }
    
    return create_response(data=data)


@router.get(
    "/live",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Service alive"},
        500: {"description": "Service not alive"}
    }
)
async def liveness_check() -> ResponseEnvelope[Dict[str, Any]]:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the service is alive and should not be restarted.
    """
    data = {
        "status": "alive",
        "timestamp": time.time(),
        "service": "capitolscope-api"
    }
    
    return create_response(data=data)


async def check_congress_api_health() -> Dict[str, Any]:
    """
    Check the health of the Congress.gov API integration.
    
    Returns:
        Dict with health status and details.
    """
    health_data = {
        "status": "unknown",
        "api_key_configured": False,
        "connectivity": False,
        "authentication": False,
        "data_availability": False,
        "last_successful_sync": None,
        "error_message": None
    }
    
    try:
        # Check if API key is configured
        if not settings.CONGRESS_GOV_API_KEY:
            health_data.update({
                "status": "unhealthy",
                "error_message": "Congress.gov API key not configured"
            })
            return health_data
        
        health_data["api_key_configured"] = True
        
        # Test API connectivity and authentication
        from domains.congressional.client import CongressAPIClient
        
        async with CongressAPIClient() as client:
            # Test basic connectivity
            try:
                response = await client.get_member_list(limit=1)
                health_data["connectivity"] = True
                health_data["authentication"] = True
                
                # Test data availability
                if response.members and len(response.members) > 0:
                    health_data["data_availability"] = True
                    health_data["status"] = "healthy"
                else:
                    health_data["status"] = "degraded"
                    health_data["error_message"] = "API accessible but no data returned"
                
            except Exception as api_error:
                health_data.update({
                    "status": "unhealthy",
                    "connectivity": False,
                    "authentication": False,
                    "error_message": f"API connection failed: {str(api_error)}"
                })
        
        # Check last successful sync (if database is available)
        try:
            from domains.congressional.models import CongressMember
            from sqlalchemy import func, select
            
            db_manager = DatabaseManager()
            if db_manager.sync_session_factory:
                with db_manager.sync_session_factory() as session:
                    # Get the most recent member update
                    result = session.execute(
                        select(func.max(CongressMember.updated_at))
                        .where(CongressMember.congress_gov_id.isnot(None))
                    )
                    last_sync = result.scalar()
                    
                    if last_sync:
                        health_data["last_successful_sync"] = last_sync.isoformat()
                    
        except Exception as db_error:
            logger.warning(f"Could not check last sync time: {db_error}")
        
    except Exception as e:
        health_data.update({
            "status": "unhealthy",
            "error_message": f"Health check failed: {str(e)}"
        })
    
    return health_data 