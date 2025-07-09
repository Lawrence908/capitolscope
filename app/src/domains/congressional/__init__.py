"""
Congressional domain for CapitolScope.

This domain handles congress members, their trades, and portfolio tracking.
Implements CAP-10 (Transaction List Page) and CAP-11 (Individual Member Profile Page).
"""

from core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "models",
    "schemas", 
    "services",
    "crud",
    "endpoints",
    "interfaces"
] 