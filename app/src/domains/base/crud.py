"""
Base CRUD operations for CapitolScope domains.

This module provides generic CRUD operations that can be extended
by domain-specific repositories.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from domains.base.models import CapitolScopeBaseModel
from domains.base.interfaces import BaseRepository
import logging
logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=CapitolScopeBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD operations implementation."""
    
    def __init__(self, model: Type[ModelType], db: Session):
        super().__init__(db)
        self.model = model
        logger.debug(f"Initialized CRUD for {model.__name__}")
    
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        try:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
            
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get a record by ID."""
        try:
            db_obj = self.db.query(self.model).filter(self.model.id == id).first()
            if db_obj:
                logger.debug(f"Retrieved {self.model.__name__} with ID: {id}")
            else:
                logger.debug(f"No {self.model.__name__} found with ID: {id}")
            return db_obj
            
        except Exception as e:
            logger.error(f"Error retrieving {self.model.__name__} with ID {id}: {e}")
            raise
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> List[ModelType]:
        """Get multiple records with pagination, filtering, and sorting."""
        try:
            query = self.db.query(self.model)
            
            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply sorting
            if sort_by:
                query = self._apply_sorting(query, sort_by, sort_order)
            
            # Apply pagination
            results = query.offset(skip).limit(limit).all()
            
            logger.debug(f"Retrieved {len(results)} {self.model.__name__} records")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving {self.model.__name__} records: {e}")
            raise
    
    def update(self, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """Update an existing record."""
        try:
            obj_data = jsonable_encoder(db_obj)
            
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)
            
            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])
            
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"Updated {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
            
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__}: {e}")
            self.db.rollback()
            raise
    
    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        try:
            db_obj = self.db.query(self.model).filter(self.model.id == id).first()
            if db_obj:
                self.db.delete(db_obj)
                self.db.commit()
                logger.info(f"Deleted {self.model.__name__} with ID: {id}")
                return True
            else:
                logger.warning(f"No {self.model.__name__} found with ID: {id} for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise
    
    def soft_delete(self, id: int) -> bool:
        """Soft delete a record by ID (if model supports it)."""
        try:
            db_obj = self.db.query(self.model).filter(self.model.id == id).first()
            if db_obj and hasattr(db_obj, 'soft_delete'):
                db_obj.soft_delete()
                self.db.commit()
                logger.info(f"Soft deleted {self.model.__name__} with ID: {id}")
                return True
            else:
                logger.warning(f"No {self.model.__name__} found with ID: {id} for soft deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error soft deleting {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        try:
            query = self.db.query(self.model)
            
            if filters:
                query = self._apply_filters(query, filters)
            
            count = query.count()
            logger.debug(f"Counted {count} {self.model.__name__} records")
            return count
            
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__} records: {e}")
            raise
    
    def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        try:
            exists = self.db.query(self.model).filter(self.model.id == id).first() is not None
            logger.debug(f"{self.model.__name__} with ID {id} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__} with ID {id}: {e}")
            raise
    
    def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get a record by a specific field value."""
        try:
            db_obj = self.db.query(self.model).filter(getattr(self.model, field) == value).first()
            if db_obj:
                logger.debug(f"Retrieved {self.model.__name__} with {field}: {value}")
            else:
                logger.debug(f"No {self.model.__name__} found with {field}: {value}")
            return db_obj
            
        except Exception as e:
            logger.error(f"Error retrieving {self.model.__name__} with {field}={value}: {e}")
            raise
    
    def get_multi_by_field(self, field: str, values: List[Any]) -> List[ModelType]:
        """Get multiple records by field values."""
        try:
            results = self.db.query(self.model).filter(getattr(self.model, field).in_(values)).all()
            logger.debug(f"Retrieved {len(results)} {self.model.__name__} records by {field}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving {self.model.__name__} records by {field}: {e}")
            raise
    
    def bulk_create(self, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records in bulk."""
        try:
            db_objs = []
            for obj_in in objs_in:
                obj_in_data = jsonable_encoder(obj_in)
                db_obj = self.model(**obj_in_data)
                db_objs.append(db_obj)
            
            self.db.add_all(db_objs)
            self.db.commit()
            
            for db_obj in db_objs:
                self.db.refresh(db_obj)
            
            logger.info(f"Bulk created {len(db_objs)} {self.model.__name__} records")
            return db_objs
            
        except Exception as e:
            logger.error(f"Error bulk creating {self.model.__name__} records: {e}")
            self.db.rollback()
            raise
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> List[ModelType]:
        """Update multiple records in bulk."""
        try:
            updated_objs = []
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                    
                db_obj = self.get(update_data['id'])
                if db_obj:
                    for field, value in update_data.items():
                        if field != 'id' and hasattr(db_obj, field):
                            setattr(db_obj, field, value)
                    updated_objs.append(db_obj)
            
            self.db.commit()
            
            for db_obj in updated_objs:
                self.db.refresh(db_obj)
            
            logger.info(f"Bulk updated {len(updated_objs)} {self.model.__name__} records")
            return updated_objs
            
        except Exception as e:
            logger.error(f"Error bulk updating {self.model.__name__} records: {e}")
            self.db.rollback()
            raise
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to a query."""
        for field, value in filters.items():
            if hasattr(self.model, field):
                if isinstance(value, dict):
                    # Handle complex filters like {"gte": 100, "lte": 200}
                    column = getattr(self.model, field)
                    if "gte" in value:
                        query = query.filter(column >= value["gte"])
                    if "lte" in value:
                        query = query.filter(column <= value["lte"])
                    if "gt" in value:
                        query = query.filter(column > value["gt"])
                    if "lt" in value:
                        query = query.filter(column < value["lt"])
                    if "in" in value:
                        query = query.filter(column.in_(value["in"]))
                    if "like" in value:
                        query = query.filter(column.like(f"%{value['like']}%"))
                elif isinstance(value, list):
                    # Handle IN filters
                    query = query.filter(getattr(self.model, field).in_(value))
                else:
                    # Handle simple equality filters
                    query = query.filter(getattr(self.model, field) == value)
        
        return query
    
    def _apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to a query."""
        if hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(asc(column))
        
        return query
    
    def search(self, query_str: str, search_fields: List[str]) -> List[ModelType]:
        """Search records across multiple fields."""
        try:
            query = self.db.query(self.model)
            
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    search_conditions.append(column.ilike(f"%{query_str}%"))
            
            if search_conditions:
                query = query.filter(or_(*search_conditions))
            
            results = query.all()
            logger.debug(f"Search returned {len(results)} {self.model.__name__} records")
            return results
            
        except Exception as e:
            logger.error(f"Error searching {self.model.__name__} records: {e}")
            raise


# Export CRUD base class
__all__ = [
    "CRUDBase",
    "ModelType",
    "CreateSchemaType", 
    "UpdateSchemaType"
] 