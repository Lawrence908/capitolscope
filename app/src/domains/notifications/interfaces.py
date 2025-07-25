"""
Notification interfaces for CapitolScope.

This module defines abstract interfaces for notification management,
including repositories, services, and delivery providers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


class NotificationRepositoryProtocol(ABC):
    """Abstract interface for notification repository operations."""
    
    @abstractmethod
    async def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user notification subscriptions."""
        pass
    
    @abstractmethod
    async def create_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification subscription."""
        pass
    
    @abstractmethod
    async def update_subscription(self, subscription_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a notification subscription."""
        pass


class EmailProviderProtocol(ABC):
    """Abstract interface for email delivery providers."""
    
    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email."""
        pass
    
    @abstractmethod
    async def send_template_email(self, to_email: str, template_id: str, variables: Dict[str, Any]) -> bool:
        """Send a templated email."""
        pass


# Log interface creation
logger.info("Notification domain interfaces initialized")

# Export all interfaces
__all__ = [
    "NotificationRepositoryProtocol",
    "EmailProviderProtocol"
] 