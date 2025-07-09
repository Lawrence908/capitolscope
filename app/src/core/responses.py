"""Standard API response envelope and utilities."""
from typing import Any, Optional, Dict, TypeVar, Generic
from pydantic import BaseModel, Field
from enum import Enum
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

T = TypeVar('T')

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard API response envelope."""
    status: ResponseStatus = Field(
        ...,
        description="Response status (success/error)"
    )
    data: Optional[T] = Field(
        None,
        description="Response data payload"
    )
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata about the response (pagination, etc.)"
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error details if status is error"
    )
    
    def to_response(self, status_code: int = 200) -> JSONResponse:
        """Convert the envelope to a proper FastAPI response object.
        
        This ensures that middleware and decorators that need to modify
        response headers have a proper Response object to work with.
        
        Args:
            status_code: HTTP status code for the response
            
        Returns:
            JSONResponse with the envelope content
        """
        return JSONResponse(
            content=jsonable_encoder(self),
            status_code=status_code
        )

def create_response(
    data: Optional[Any] = None,
    error: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a standard API response envelope.
    
    Args:
        data: Response data payload
        error: Error details if any
        meta: Response metadata
        status_code: HTTP status code
        request_id: Request ID for tracing
        
    Returns:
        Response envelope with standardized format
    """
    if error:
        status = ResponseStatus.ERROR
    else:
        status = ResponseStatus.SUCCESS
        
    if meta is None:
        meta = {}
    
    if request_id:
        meta["request_id"] = request_id
        
    envelope = ResponseEnvelope(
        status=status,
        data=data,
        meta=meta,
        error=error
    )
    return envelope.to_response(status_code)


# Convenience functions for common response types
def success_response(
    data: Any,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a success response."""
    return create_response(
        data=data,
        meta=meta,
        status_code=status_code,
        request_id=request_id
    )


def error_response(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create an error response."""
    error = {
        "message": message,
        "code": error_code or "unknown_error"
    }
    
    if details:
        error.update(details)
    
    return create_response(
        error=error,
        status_code=status_code,
        request_id=request_id
    )


def paginated_response(
    data: Any,
    page: int,
    page_size: int,
    total_items: int,
    total_pages: int,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a paginated response."""
    meta = {
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
    
    return success_response(
        data=data,
        meta=meta,
        request_id=request_id
    ) 