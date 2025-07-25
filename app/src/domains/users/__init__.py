"""
Users domain for CapitolScope.

This domain handles user authentication, subscriptions, preferences, and notifications.
Implements user management and premium features infrastructure.
"""

import logging
logger = logging.getLogger(__name__)

__all__ = [
    "models",
    "schemas", 
    "services",
    "crud",
    "endpoints",
    "interfaces"
] 