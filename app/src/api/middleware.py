"""
Custom middleware for FastAPI application.
"""

import time
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            "HTTP request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "HTTP request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Initialize client request history
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        # Clean old requests (older than 1 minute)
        minute_ago = current_time - 60
        self.client_requests[client_ip] = [
            req_time for req_time in self.client_requests[client_ip]
            if req_time > minute_ago
        ]
        
        # Check if rate limit exceeded
        if len(self.client_requests[client_ip]) >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_count=len(self.client_requests[client_ip]),
                limit=self.requests_per_minute,
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "type": "rate_limit_exceeded",
                        "code": 429,
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60,
                    }
                },
                headers={"Retry-After": "60"},
            )
        
        # Add current request to history
        self.client_requests[client_ip].append(current_time)
        
        # Process request
        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        
        except Exception as exc:
            logger.error(
                "Unhandled exception in middleware",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                exc_info=True,
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_error",
                        "code": 500,
                        "message": "An internal server error occurred",
                        "path": request.url.path,
                    }
                },
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response 