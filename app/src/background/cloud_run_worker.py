"""
Cloud Run Background Worker Service

This service handles background tasks in a Cloud Run environment by:
1. Exposing HTTP endpoints for task triggering
2. Using Redis for task queuing
3. Processing tasks asynchronously
4. Providing health checks and monitoring
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis

from core.config import get_settings
from core.database import DatabaseManager
from background.tasks import (
    _sync_congressional_members_async,
    _comprehensive_data_ingestion_async,
    _update_stock_prices_async,
    _process_pending_notifications_async,
    _health_check_congress_api_async,
    system_health_check
)

# Configure logging for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="CapitolScope Background Worker", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for task queuing
redis_client: Optional[redis.Redis] = None

class TaskRequest(BaseModel):
    task_name: str
    parameters: Dict[str, Any] = {}
    priority: int = 5

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection and other startup tasks."""
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("Database connection established")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections."""
    global redis_client
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "capitolscope-worker"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including dependencies."""
    try:
        # Check Redis
        redis_status = "healthy"
        try:
            await redis_client.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        # Check database
        db_status = "healthy"
        try:
            db_manager = DatabaseManager()
            await db_manager.initialize()
            async with db_manager.session_factory() as session:
                await session.execute("SELECT 1")
            await db_manager.close()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        overall_status = "healthy" if redis_status == "healthy" and db_status == "healthy" else "unhealthy"
        
        return {
            "status": overall_status,
            "components": {
                "redis": redis_status,
                "database": db_status
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TASK EXECUTION ENDPOINTS
# ============================================================================

@app.post("/tasks/execute")
async def execute_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Execute a background task immediately."""
    task_id = f"task_{int(datetime.utcnow().timestamp())}"
    
    try:
        logger.info(f"Executing task: {task_request.task_name} with ID: {task_id}")
        
        # Add task to background processing
        background_tasks.add_task(
            _execute_task_async,
            task_id,
            task_request.task_name,
            task_request.parameters
        )
        
        return TaskResponse(
            task_id=task_id,
            status="queued",
            message=f"Task {task_request.task_name} queued for execution",
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to queue task {task_request.task_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _execute_task_async(task_id: str, task_name: str, parameters: Dict[str, Any]):
    """Execute task asynchronously."""
    try:
        logger.info(f"Starting task execution: {task_name} ({task_id})")
        start_time = datetime.utcnow()
        
        result = await _route_task_execution(task_name, parameters)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Task completed: {task_name} ({task_id}) in {duration:.2f}s")
        
        # Store result in Redis for status checking
        await redis_client.setex(
            f"task_result:{task_id}",
            3600,  # 1 hour expiry
            str(result)
        )
        
    except Exception as e:
        logger.error(f"Task execution failed: {task_name} ({task_id}): {e}")
        await redis_client.setex(
            f"task_result:{task_id}",
            3600,
            f"ERROR: {str(e)}"
        )

async def _route_task_execution(task_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Route task execution to appropriate function."""
    
    task_map = {
        "sync_congressional_members": lambda: _sync_congressional_members_async(
            parameters.get("action", "sync-all"), **parameters
        ),
        "comprehensive_data_ingestion": lambda: _comprehensive_data_ingestion_async(),
        "update_stock_prices": lambda: _update_stock_prices_async(
            parameters.get("symbols")
        ),
        "process_pending_notifications": lambda: _process_pending_notifications_async(),
        "health_check_congress_api": lambda: _health_check_congress_api_async(),
        "system_health_check": lambda: system_health_check.delay().get()
    }
    
    if task_name not in task_map:
        raise ValueError(f"Unknown task: {task_name}")
    
    return await task_map[task_name]()

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get task execution status."""
    try:
        result = await redis_client.get(f"task_result:{task_id}")
        
        if result is None:
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": "Task not found or expired"
            }
        
        if result.startswith("ERROR:"):
            return {
                "task_id": task_id,
                "status": "failed",
                "error": result[6:],  # Remove "ERROR:" prefix
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SCHEDULED TASK ENDPOINTS (Cloud Scheduler Integration)
# ============================================================================

@app.post("/scheduled/congressional-sync")
async def scheduled_congressional_sync(request: Request, background_tasks: BackgroundTasks):
    """Endpoint for Cloud Scheduler to trigger congressional data sync."""
    # Verify request is from Cloud Scheduler (optional)
    user_agent = request.headers.get("user-agent", "")
    if not user_agent.startswith("Google-Cloud-Scheduler"):
        logger.warning(f"Unexpected user agent: {user_agent}")
    
    task_id = f"scheduled_congressional_sync_{int(datetime.utcnow().timestamp())}"
    
    background_tasks.add_task(
        _execute_task_async,
        task_id,
        "comprehensive_data_ingestion",
        {}
    )
    
    return {"status": "scheduled", "task_id": task_id}

@app.post("/scheduled/stock-prices")
async def scheduled_stock_prices(request: Request, background_tasks: BackgroundTasks):
    """Endpoint for Cloud Scheduler to trigger stock price updates."""
    task_id = f"scheduled_stock_prices_{int(datetime.utcnow().timestamp())}"
    
    background_tasks.add_task(
        _execute_task_async,
        task_id,
        "update_stock_prices",
        {}
    )
    
    return {"status": "scheduled", "task_id": task_id}

@app.post("/scheduled/notifications")
async def scheduled_notifications(request: Request, background_tasks: BackgroundTasks):
    """Endpoint for Cloud Scheduler to trigger notification processing."""
    task_id = f"scheduled_notifications_{int(datetime.utcnow().timestamp())}"
    
    background_tasks.add_task(
        _execute_task_async,
        task_id,
        "process_pending_notifications",
        {}
    )
    
    return {"status": "scheduled", "task_id": task_id}

@app.post("/scheduled/health-check")
async def scheduled_health_check(request: Request, background_tasks: BackgroundTasks):
    """Endpoint for Cloud Scheduler to trigger health checks."""
    task_id = f"scheduled_health_check_{int(datetime.utcnow().timestamp())}"
    
    background_tasks.add_task(
        _execute_task_async,
        task_id,
        "health_check_congress_api",
        {}
    )
    
    return {"status": "scheduled", "task_id": task_id}

# ============================================================================
# MONITORING AND ADMIN ENDPOINTS
# ============================================================================

@app.get("/admin/queue-status")
async def get_queue_status():
    """Get queue status and metrics."""
    try:
        # Get Redis info
        info = await redis_client.info()
        
        # Get task counts (simplified for Cloud Run)
        pending_tasks = 0  # Would need more complex tracking in production
        
        return {
            "redis": {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            },
            "tasks": {
                "pending": pending_tasks,
                "processing": 0  # Would track active background tasks
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/recent-tasks")
async def get_recent_tasks():
    """Get recent task execution history."""
    try:
        # In a full implementation, you'd store task history in Redis/database
        # For now, return a placeholder
        return {
            "recent_tasks": [],
            "message": "Task history tracking not yet implemented",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
