"""
Base service layer for CapitolScope domains.

This module provides generic service patterns that can be extended
by domain-specific business logic implementations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy.orm import Session

from domains.base.interfaces import BaseService, BaseRepository
from domains.base.crud import CRUDBase
from domains.base.models import CapitolScopeBaseModel
from core.logging import get_logger

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=CapitolScopeBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class ServiceBase(BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """Base service implementation with common business logic patterns."""
    
    def __init__(
        self,
        repository: BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType],
        response_model: Type[ResponseSchemaType]
    ):
        super().__init__(repository)
        self.response_model = response_model
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    def create(self, obj_in: CreateSchemaType, **kwargs) -> ResponseSchemaType:
        """Create a new record with business logic."""
        try:
            logger.info(f"Creating new {self.response_model.__name__}")
            
            # Pre-creation validation
            self._validate_create(obj_in, **kwargs)
            
            # Create the record
            db_obj = self.repository.create(obj_in)
            
            # Post-creation processing
            self._post_create(db_obj, **kwargs)
            
            # Convert to response schema
            response = self.response_model.model_validate(db_obj)
            logger.info(f"Successfully created {self.response_model.__name__} with ID: {db_obj.id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating {self.response_model.__name__}: {e}")
            raise
    
    def get(self, id: int, **kwargs) -> Optional[ResponseSchemaType]:
        """Get a record by ID with business logic."""
        try:
            logger.debug(f"Retrieving {self.response_model.__name__} with ID: {id}")
            
            # Pre-retrieval validation
            self._validate_get(id, **kwargs)
            
            # Get the record
            db_obj = self.repository.get(id)
            
            if not db_obj:
                logger.debug(f"No {self.response_model.__name__} found with ID: {id}")
                return None
            
            # Post-retrieval processing
            self._post_get(db_obj, **kwargs)
            
            # Convert to response schema
            response = self.response_model.model_validate(db_obj)
            logger.debug(f"Successfully retrieved {self.response_model.__name__} with ID: {id}")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving {self.response_model.__name__} with ID {id}: {e}")
            raise
    
    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[ResponseSchemaType]:
        """Get multiple records with business logic."""
        try:
            logger.debug(f"Retrieving multiple {self.response_model.__name__} records")
            
            # Pre-retrieval validation
            self._validate_get_multi(skip, limit, filters, **kwargs)
            
            # Get the records
            db_objs = self.repository.get_multi(skip=skip, limit=limit, filters=filters)
            
            # Post-retrieval processing
            self._post_get_multi(db_objs, **kwargs)
            
            # Convert to response schemas
            responses = [self.response_model.model_validate(db_obj) for db_obj in db_objs]
            logger.debug(f"Successfully retrieved {len(responses)} {self.response_model.__name__} records")
            return responses
            
        except Exception as e:
            logger.error(f"Error retrieving multiple {self.response_model.__name__} records: {e}")
            raise
    
    def update(self, id: int, obj_in: UpdateSchemaType, **kwargs) -> ResponseSchemaType:
        """Update a record with business logic."""
        try:
            logger.info(f"Updating {self.response_model.__name__} with ID: {id}")
            
            # Pre-update validation
            self._validate_update(id, obj_in, **kwargs)
            
            # Get existing record
            db_obj = self.repository.get(id)
            if not db_obj:
                raise ValueError(f"No {self.response_model.__name__} found with ID: {id}")
            
            # Update the record
            db_obj = self.repository.update(db_obj, obj_in)
            
            # Post-update processing
            self._post_update(db_obj, **kwargs)
            
            # Convert to response schema
            response = self.response_model.model_validate(db_obj)
            logger.info(f"Successfully updated {self.response_model.__name__} with ID: {id}")
            return response
            
        except Exception as e:
            logger.error(f"Error updating {self.response_model.__name__} with ID {id}: {e}")
            raise
    
    def delete(self, id: int, **kwargs) -> bool:
        """Delete a record with business logic."""
        try:
            logger.info(f"Deleting {self.response_model.__name__} with ID: {id}")
            
            # Pre-deletion validation
            self._validate_delete(id, **kwargs)
            
            # Get existing record for post-deletion processing
            db_obj = self.repository.get(id)
            if not db_obj:
                logger.warning(f"No {self.response_model.__name__} found with ID: {id}")
                return False
            
            # Delete the record
            result = self.repository.delete(id)
            
            # Post-deletion processing
            if result:
                self._post_delete(db_obj, **kwargs)
            
            logger.info(f"Successfully deleted {self.response_model.__name__} with ID: {id}")
            return result
            
        except Exception as e:
            logger.error(f"Error deleting {self.response_model.__name__} with ID {id}: {e}")
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None, **kwargs) -> int:
        """Count records with business logic."""
        try:
            logger.debug(f"Counting {self.response_model.__name__} records")
            
            # Pre-count validation
            self._validate_count(filters, **kwargs)
            
            # Count the records
            count = self.repository.count(filters)
            
            logger.debug(f"Successfully counted {count} {self.response_model.__name__} records")
            return count
            
        except Exception as e:
            logger.error(f"Error counting {self.response_model.__name__} records: {e}")
            raise
    
    def exists(self, id: int, **kwargs) -> bool:
        """Check if a record exists with business logic."""
        try:
            logger.debug(f"Checking existence of {self.response_model.__name__} with ID: {id}")
            
            # Pre-existence validation
            self._validate_exists(id, **kwargs)
            
            # Check existence
            exists = self.repository.exists(id)
            
            logger.debug(f"{self.response_model.__name__} with ID {id} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking existence of {self.response_model.__name__} with ID {id}: {e}")
            raise
    
    def search(self, query: str, search_fields: List[str], **kwargs) -> List[ResponseSchemaType]:
        """Search records with business logic."""
        try:
            logger.debug(f"Searching {self.response_model.__name__} records")
            
            # Pre-search validation
            self._validate_search(query, search_fields, **kwargs)
            
            # Perform search
            if hasattr(self.repository, 'search'):
                db_objs = self.repository.search(query, search_fields)
            else:
                logger.warning(f"Search not implemented for {self.repository.__class__.__name__}")
                return []
            
            # Post-search processing
            self._post_search(db_objs, **kwargs)
            
            # Convert to response schemas
            responses = [self.response_model.model_validate(db_obj) for db_obj in db_objs]
            logger.debug(f"Search returned {len(responses)} {self.response_model.__name__} records")
            return responses
            
        except Exception as e:
            logger.error(f"Error searching {self.response_model.__name__} records: {e}")
            raise
    
    # ============================================================================
    # VALIDATION HOOKS (Override in subclasses)
    # ============================================================================
    
    def _validate_create(self, obj_in: CreateSchemaType, **kwargs) -> None:
        """Validate before creating a record."""
        pass
    
    def _validate_get(self, id: int, **kwargs) -> None:
        """Validate before retrieving a record."""
        pass
    
    def _validate_get_multi(self, skip: int, limit: int, filters: Optional[Dict[str, Any]], **kwargs) -> None:
        """Validate before retrieving multiple records."""
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")
    
    def _validate_update(self, id: int, obj_in: UpdateSchemaType, **kwargs) -> None:
        """Validate before updating a record."""
        pass
    
    def _validate_delete(self, id: int, **kwargs) -> None:
        """Validate before deleting a record."""
        pass
    
    def _validate_count(self, filters: Optional[Dict[str, Any]], **kwargs) -> None:
        """Validate before counting records."""
        pass
    
    def _validate_exists(self, id: int, **kwargs) -> None:
        """Validate before checking existence."""
        pass
    
    def _validate_search(self, query: str, search_fields: List[str], **kwargs) -> None:
        """Validate before searching records."""
        if not query.strip():
            raise ValueError("Search query cannot be empty")
    
    # ============================================================================
    # PROCESSING HOOKS (Override in subclasses)
    # ============================================================================
    
    def _post_create(self, db_obj: ModelType, **kwargs) -> None:
        """Process after creating a record."""
        pass
    
    def _post_get(self, db_obj: ModelType, **kwargs) -> None:
        """Process after retrieving a record."""
        pass
    
    def _post_get_multi(self, db_objs: List[ModelType], **kwargs) -> None:
        """Process after retrieving multiple records."""
        pass
    
    def _post_update(self, db_obj: ModelType, **kwargs) -> None:
        """Process after updating a record."""
        pass
    
    def _post_delete(self, db_obj: ModelType, **kwargs) -> None:
        """Process after deleting a record."""
        pass
    
    def _post_search(self, db_objs: List[ModelType], **kwargs) -> None:
        """Process after searching records."""
        pass
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _enrich_response(self, response: ResponseSchemaType, **kwargs) -> ResponseSchemaType:
        """Enrich response with additional data."""
        return response
    
    def _apply_business_rules(self, obj: Union[CreateSchemaType, UpdateSchemaType], **kwargs) -> None:
        """Apply business rules to an object."""
        pass
    
    def _audit_operation(self, operation: str, obj_id: Optional[int] = None, **kwargs) -> None:
        """Audit an operation."""
        logger.info(f"Auditing operation: {operation} on {self.response_model.__name__}")
    
    def _cache_response(self, key: str, response: ResponseSchemaType, ttl: int = 300) -> None:
        """Cache a response."""
        # Implement caching logic here
        pass
    
    def _get_cached_response(self, key: str) -> Optional[ResponseSchemaType]:
        """Get a cached response."""
        # Implement cache retrieval logic here
        return None
    
    def _send_notification(self, event: str, data: Dict[str, Any]) -> None:
        """Send a notification."""
        logger.info(f"Sending notification for event: {event}")
    
    def _track_metrics(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Track performance metrics."""
        logger.debug(f"Tracking metric: {metric_name} = {value}")


# Utility functions
def create_service_with_crud(
    model: Type[ModelType],
    create_schema: Type[CreateSchemaType],
    update_schema: Type[UpdateSchemaType],
    response_schema: Type[ResponseSchemaType],
    db: Session
) -> ServiceBase[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]:
    """Create a service instance with CRUD repository."""
    crud_repo = CRUDBase(model, db)
    service = ServiceBase(crud_repo, response_schema)
    return service


# Export service base class
__all__ = [
    "ServiceBase",
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType", 
    "ResponseSchemaType",
    "create_service_with_crud"
] 