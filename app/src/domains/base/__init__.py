"""
Base domain for CapitolScope.

This domain contains common utilities, schemas, and shared functionality
that is used across multiple domains.
"""

from core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "models",
    "schemas", 
    "services",
    "crud",
    "interfaces"
] 