"""
Users domain for CapitolScope.

This domain handles user authentication, subscriptions, preferences, and notifications.
Implements user management and premium features infrastructure.
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