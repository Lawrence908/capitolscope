"""
Core exception classes for CapitolScope.

This module defines custom exceptions used throughout the application
for consistent error handling and user feedback.
"""

from typing import Any, Dict, Optional


class CapitolScopeException(Exception):
    """Base exception class for CapitolScope."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(CapitolScopeException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found with identifier: {identifier}"
        super().__init__(message, details)
        self.resource = resource
        self.identifier = identifier


class ValidationError(CapitolScopeException):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.field = field


class AuthenticationError(CapitolScopeException):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class AuthorizationError(CapitolScopeException):
    """Exception raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class DatabaseError(CapitolScopeException):
    """Exception raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.operation = operation


class ExternalAPIError(CapitolScopeException):
    """Exception raised when external API calls fail."""
    
    def __init__(self, message: str, api_name: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code


class ConfigurationError(CapitolScopeException):
    """Exception raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.config_key = config_key


class DataIngestionError(CapitolScopeException):
    """Exception raised when data ingestion fails."""
    
    def __init__(self, message: str, source: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.source = source


class RateLimitError(CapitolScopeException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.retry_after = retry_after


class CacheError(CapitolScopeException):
    """Exception raised when cache operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.operation = operation


class NotificationError(CapitolScopeException):
    """Exception raised when notification sending fails."""
    
    def __init__(self, message: str, channel: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.channel = channel


# Export all exceptions
__all__ = [
    "CapitolScopeException",
    "NotFoundError", 
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError", 
    "DatabaseError",
    "ExternalAPIError",
    "ConfigurationError",
    "DataIngestionError",
    "RateLimitError",
    "CacheError",
    "NotificationError"
] 