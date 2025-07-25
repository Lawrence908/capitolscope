"""
Base domain for CapitolScope.

This domain contains common utilities, schemas, and shared functionality
that is used across multiple domains.
"""

import logging
logger = logging.getLogger(__name__)

__all__ = [
    "models",
    "schemas", 
    "services",
    "crud",
    "interfaces"
] 