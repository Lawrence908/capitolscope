"""
Base database models for CapitolScope.

This module defines the base model classes and common database configurations
that are used across all domains.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from core.logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class BaseModel:
    """Base mixin class for all models."""
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TimestampMixin:
    """Mixin for models with created_at and updated_at timestamps."""
    
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=True)


class SoftDeleteMixin:
    """Mixin for models with soft delete capability."""
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    def soft_delete(self):
        """Mark record as deleted without removing it."""
        self.is_deleted = True
        self.deleted_at = func.now()


class AuditMixin:
    """Mixin for models that need audit tracking."""
    
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    def set_created_by(self, user_id: str):
        """Set the creator of the record."""
        self.created_by = user_id
    
    def set_updated_by(self, user_id: str):
        """Set the updater of the record."""
        self.updated_by = user_id


class ActiveRecordMixin:
    """Mixin for models with active/inactive status."""
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    def activate(self):
        """Mark record as active."""
        self.is_active = True
        logger.info(f"Activated {self.__class__.__name__} with ID: {getattr(self, 'id', None)}")
    
    def deactivate(self):
        """Mark record as inactive."""
        self.is_active = False
        logger.info(f"Deactivated {self.__class__.__name__} with ID: {getattr(self, 'id', None)}")


class MetadataMixin:
    """Mixin for models that need metadata storage."""
    
    from sqlalchemy.dialects.postgresql import JSONB
    
    extra_data = Column(JSONB, nullable=True)
    
    def set_metadata(self, key: str, value: any):
        """Set metadata key-value pair."""
        if self.extra_data is None:
            self.extra_data = {}
        self.extra_data[key] = value
    
    def get_metadata(self, key: str, default=None):
        """Get metadata value by key."""
        if self.extra_data is None:
            return default
        return self.extra_data.get(key, default)


# Combined base model with common functionality
class CapitolScopeBaseModel(Base, BaseModel, TimestampMixin):
    """Base model for all CapitolScope database models."""
    
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug(f"Created {self.__class__.__name__} instance")


# Common validation functions
def validate_positive_integer(value: int, field_name: str) -> int:
    """Validate that an integer is positive."""
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Validate that a string is not empty."""
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip() if value else None


def validate_email_format(email: str) -> str:
    """Basic email format validation."""
    import re
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")
    return email


def validate_phone_format(phone: str) -> str:
    """Basic phone number format validation."""
    import re
    if phone and not re.match(r'^\+?1?\d{9,15}$', phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
        raise ValueError("Invalid phone number format")
    return phone


# Database connection and session management utilities
def get_db_url():
    """Get database URL from configuration."""
    from core.config import settings
    return settings.DATABASE_URL


def create_engine():
    """Create database engine with proper configuration."""
    from sqlalchemy import create_engine
    from core.config import settings
    
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    logger.info("Database engine created successfully")
    return engine


def create_session_factory():
    """Create session factory for database operations."""
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    logger.info("Database session factory created")
    return SessionLocal


def get_db_session():
    """Get database session for dependency injection."""
    SessionLocal = create_session_factory()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# Export all base components
__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin", 
    "AuditMixin",
    "ActiveRecordMixin",
    "MetadataMixin",
    "CapitolScopeBaseModel",
    "validate_positive_integer",
    "validate_non_empty_string",
    "validate_email_format",
    "validate_phone_format",
    "get_db_url",
    "create_engine",
    "create_session_factory",
    "get_db_session"
] 