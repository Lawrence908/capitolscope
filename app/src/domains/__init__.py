"""
Domain-driven architecture for CapitolScope.

This package contains all business domains organized by functionality:
- admin: System monitoring, audit logs, configuration
- analytics: Performance metrics, reporting, data analysis  
- congressional: Congress members, trades, portfolios
- notifications: Email campaigns, user notifications, alerts
- portfolio: Portfolio management, performance tracking
- securities: Stocks, prices, exchanges, asset types
- social: Social media integration, community features
- users: Authentication, subscriptions, preferences
- base: Common utilities, schemas, and shared functionality

Each domain follows a consistent structure:
- models.py: SQLAlchemy ORM models
- schemas.py: Pydantic validation schemas
- services.py: Business logic layer
- crud.py: Database operations
- endpoints.py: FastAPI route handlers
- interfaces.py: Abstract interfaces and protocols
"""

from core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "admin",
    "analytics", 
    "congressional",
    "notifications",
    "portfolio",
    "securities",
    "social",
    "users",
    "base"
] 