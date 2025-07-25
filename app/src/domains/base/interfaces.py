"""
Base interfaces and protocols for CapitolScope domains.

This module defines abstract interfaces and protocols that establish
contracts for domain implementations across the application.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Protocol, runtime_checkable
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

import logging
logger = logging.getLogger(__name__)

# Type variables for generic interfaces
ModelType = TypeVar('ModelType')
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)
ResponseSchemaType = TypeVar('ResponseSchemaType', bound=BaseModel)


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class BaseRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Abstract base repository interface for CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        pass
    
    @abstractmethod
    def get(self, id: UUID) -> Optional[ModelType]:
        """Get a record by ID."""
        pass
    
    @abstractmethod
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering."""
        pass
    
    @abstractmethod
    def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update an existing record."""
        pass
    
    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        pass


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class BaseService(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """Abstract base service interface for business logic."""
    
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def create(self, obj_in: CreateSchemaType) -> ResponseSchemaType:
        """Create a new record with business logic."""
        pass
    
    @abstractmethod
    def get(self, id: int) -> Optional[ResponseSchemaType]:
        """Get a record by ID with business logic."""
        pass
    
    @abstractmethod
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ResponseSchemaType]:
        """Get multiple records with business logic."""
        pass
    
    @abstractmethod
    def update(self, id: int, obj_in: UpdateSchemaType) -> ResponseSchemaType:
        """Update a record with business logic."""
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        """Delete a record with business logic."""
        pass


# ============================================================================
# DOMAIN PROTOCOLS
# ============================================================================

@runtime_checkable
class Searchable(Protocol):
    """Protocol for searchable entities."""
    
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Search for entities matching the query."""
        ...


@runtime_checkable
class Cacheable(Protocol):
    """Protocol for cacheable entities."""
    
    def get_cache_key(self) -> str:
        """Get the cache key for this entity."""
        ...
    
    def get_cache_ttl(self) -> int:
        """Get the cache TTL in seconds."""
        ...


@runtime_checkable
class Auditable(Protocol):
    """Protocol for auditable entities."""
    
    def get_audit_data(self) -> Dict[str, Any]:
        """Get audit data for this entity."""
        ...


@runtime_checkable
class Exportable(Protocol):
    """Protocol for exportable entities."""
    
    def to_csv(self) -> str:
        """Export entity to CSV format."""
        ...
    
    def to_json(self) -> Dict[str, Any]:
        """Export entity to JSON format."""
        ...


@runtime_checkable
class Notifiable(Protocol):
    """Protocol for entities that can send notifications."""
    
    def send_notification(self, message: str, channels: List[str]) -> bool:
        """Send notification through specified channels."""
        ...


# ============================================================================
# DATA ACCESS INTERFACES
# ============================================================================

class DataIngestionInterface(ABC):
    """Abstract interface for data ingestion operations."""
    
    @abstractmethod
    def ingest_data(self, source: str, data: Any) -> Dict[str, Any]:
        """Ingest data from a source."""
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """Validate data before ingestion."""
        pass
    
    @abstractmethod
    def transform_data(self, data: Any) -> Any:
        """Transform data during ingestion."""
        pass


class DataExportInterface(ABC):
    """Abstract interface for data export operations."""
    
    @abstractmethod
    def export_data(self, format: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Export data in specified format."""
        pass
    
    @abstractmethod
    def get_export_formats(self) -> List[str]:
        """Get available export formats."""
        pass


class DataSyncInterface(ABC):
    """Abstract interface for data synchronization operations."""
    
    @abstractmethod
    def sync_data(self, source: str, target: str) -> Dict[str, Any]:
        """Synchronize data between source and target."""
        pass
    
    @abstractmethod
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        pass


# ============================================================================
# EXTERNAL SERVICE INTERFACES
# ============================================================================

class ExternalAPIInterface(ABC):
    """Abstract interface for external API integrations."""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the external API."""
        pass
    
    @abstractmethod
    def make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """Make a request to the external API."""
        pass
    
    @abstractmethod
    def handle_rate_limit(self) -> None:
        """Handle rate limiting."""
        pass


class NotificationInterface(ABC):
    """Abstract interface for notification services."""
    
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email notification."""
        pass
    
    @abstractmethod
    def send_push_notification(self, user_id: str, message: str) -> bool:
        """Send push notification."""
        pass
    
    @abstractmethod
    def send_sms(self, phone: str, message: str) -> bool:
        """Send SMS notification."""
        pass


class CacheInterface(ABC):
    """Abstract interface for caching operations."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass


# ============================================================================
# ANALYTICS INTERFACES
# ============================================================================

class AnalyticsInterface(ABC):
    """Abstract interface for analytics operations."""
    
    @abstractmethod
    def track_event(self, event_name: str, properties: Dict[str, Any]) -> None:
        """Track an analytics event."""
        pass
    
    @abstractmethod
    def get_metrics(self, metric_name: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get analytics metrics."""
        pass
    
    @abstractmethod
    def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Any:
        """Generate analytics report."""
        pass


class PerformanceTrackingInterface(ABC):
    """Abstract interface for performance tracking."""
    
    @abstractmethod
    def start_timing(self, operation_name: str) -> str:
        """Start timing an operation."""
        pass
    
    @abstractmethod
    def end_timing(self, timer_id: str) -> float:
        """End timing and return duration."""
        pass
    
    @abstractmethod
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a performance metric."""
        pass


# ============================================================================
# SECURITY INTERFACES
# ============================================================================

class AuthenticationInterface(ABC):
    """Abstract interface for authentication operations."""
    
    @abstractmethod
    def authenticate_user(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate a user."""
        pass
    
    @abstractmethod
    def generate_token(self, user_id: str, permissions: List[str]) -> str:
        """Generate authentication token."""
        pass
    
    @abstractmethod
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate authentication token."""
        pass


class AuthorizationInterface(ABC):
    """Abstract interface for authorization operations."""
    
    @abstractmethod
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission for action on resource."""
        pass
    
    @abstractmethod
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user."""
        pass
    
    @abstractmethod
    def assign_permission(self, user_id: str, permission: str) -> bool:
        """Assign permission to user."""
        pass


class EncryptionInterface(ABC):
    """Abstract interface for encryption operations."""
    
    @abstractmethod
    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        pass
    
    @abstractmethod
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        pass
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        pass


# ============================================================================
# VALIDATION INTERFACES
# ============================================================================

class ValidationInterface(ABC):
    """Abstract interface for validation operations."""
    
    @abstractmethod
    def validate(self, data: Any, schema: Any) -> Dict[str, Any]:
        """Validate data against schema."""
        pass
    
    @abstractmethod
    def get_validation_errors(self, data: Any, schema: Any) -> List[str]:
        """Get validation errors."""
        pass


# ============================================================================
# UTILITY INTERFACES
# ============================================================================

class ConfigurationInterface(ABC):
    """Abstract interface for configuration management."""
    
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting."""
        pass
    
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> bool:
        """Set configuration setting."""
        pass
    
    @abstractmethod
    def reload_configuration(self) -> None:
        """Reload configuration from source."""
        pass


class LoggingInterface(ABC):
    """Abstract interface for logging operations."""
    
    @abstractmethod
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        pass
    
    @abstractmethod
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        pass
    
    @abstractmethod
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        pass


# Export all interfaces
__all__ = [
    "ModelType",
    "CreateSchemaType", 
    "UpdateSchemaType",
    "ResponseSchemaType",
    "BaseRepository",
    "BaseService",
    "Searchable",
    "Cacheable",
    "Auditable",
    "Exportable",
    "Notifiable",
    "DataIngestionInterface",
    "DataExportInterface",
    "DataSyncInterface",
    "ExternalAPIInterface",
    "NotificationInterface",
    "CacheInterface",
    "AnalyticsInterface",
    "PerformanceTrackingInterface",
    "AuthenticationInterface",
    "AuthorizationInterface",
    "EncryptionInterface",
    "ValidationInterface",
    "ConfigurationInterface",
    "LoggingInterface"
] 