# app/services/servicemixin.py
from typing import TypeVar, Generic, Optional, List, Any, Dict, Type
import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, and_

from app.schemas.common import Page

T = TypeVar('T', bound=SQLModel)
ID = TypeVar('ID', int, uuid.UUID, str)

# Service Mixins
class CRUDMixin(Generic[T]):
    """Generic CRUD operations for SQLModel models."""
    model: Type[T]
    
    # Create operations
    async def create(self, obj_in: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> T:
        """Create a new record."""
        obj_in = await self._before_create(obj_in, session, user_id)
            
        session.add(obj_in)
        await session.commit()
        await session.refresh(obj_in)
        
        await self._after_create(obj_in, session, user_id)
        return obj_in
    
    async def bulk_create(self, objs_in: List[T], session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> List[T]:
        """Create multiple records in one transaction."""
        for obj in objs_in:
            await self._before_create(obj, session, user_id)
            if hasattr(obj, "created_by") and user_id is not None:
                obj.created_by = user_id
            if hasattr(obj, "updated_by") and user_id is not None:
                obj.updated_by = user_id
                
        session.add_all(objs_in)
        await session.commit()
        
        for obj in objs_in:
            await session.refresh(obj)
            await self._after_create(obj, session, user_id)
            
        return objs_in
    
    #check if user is superuser
    async def is_superuser(self, user_id: uuid.UUID, session: AsyncSession) -> bool:
        """Check if a user is a superuser."""
        statement = select(self.model).where(
            getattr(self.model, "id") == user_id,
            getattr(self.model, "is_superuser") == True
        )
        result = await session.execute(statement)
        return result.scalars().first() is not None
    
    # Read operations
    async def get(self, id: ID, session: AsyncSession) -> Optional[T]:
        """Get a record by ID."""
        return await session.get(self.model, id)
    
    async def get_with_related(self, id: ID, session: AsyncSession, *relations) -> Optional[T]:
        """Get a record with its related entities eager-loaded."""
        statement = select(self.model).where(getattr(self.model, "id") == id)
        for relation in relations:
            statement = statement.options(selectinload(relation))
        result = await session.execute(statement)
        return result.scalars().first()
    
    async def get_by_field(self, field_name: str, value: Any, session: AsyncSession) -> Optional[T]:
        """Get a record by a specific field value."""
        statement = select(self.model).where(getattr(self.model, field_name) == value)
        result = await session.execute(statement)
        return result.scalars().first()
    
    async def filter(self, session: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> Page[T]:
        """Get records matching the provided filters."""
        query = select(self.model)
        
        # Apply filters
        conditions = []
        for field, value in filters.items():
            if hasattr(self.model, field):
                if isinstance(value, list):
                    conditions.append(getattr(self.model, field).in_(value))
                else:
                    conditions.append(getattr(self.model, field) == value)
        
        if conditions:
            query = query.where(and_(*conditions))
            
        # Handle soft-deleted records
        if hasattr(self.model, "deleted_at"):
            query = query.where(getattr(self.model, "deleted_at").is_(None))
            
        return await self._execute_paginated_query(query, session, skip, limit)
    
    async def search(self, session: AsyncSession, search_term: str, search_fields: List[str], skip: int = 0, limit: int = 100) -> Page[T]:
        """Search for records matching the search term in specified fields."""
        query = select(self.model)
        
        if search_term:
            conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    conditions.append(getattr(self.model, field).ilike(f'%{search_term}%'))
            
            if conditions:
                query = query.where(or_(*conditions))
                
        # Handle soft-deleted records
        if hasattr(self.model, "deleted_at"):
            query = query.where(getattr(self.model, "deleted_at").is_(None))
            
        return await self._execute_paginated_query(query, session, skip, limit)
    
    async def list(self, session: AsyncSession, skip: int = 0, limit: int = 100, include_deleted: bool = False, order_by: str = "created_by", order_desc: bool = False) -> Page[T]:
        """List records with pagination."""
        query = select(self.model)
        
        # Handle soft-deleted records
        if hasattr(self.model, "deleted_at") and not include_deleted:
            query = query.where(getattr(self.model, "deleted_at").is_(None))
        
        # Order by the specified column
        if hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_desc:
                order_column = order_column.desc()
            query = query.order_by(order_column)
            
        return await self._execute_paginated_query(query, session, skip, limit)
    
    # Update operations
    async def update(self, id: ID, obj_in: Dict[str, Any], session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """Update a record."""
        db_obj = await self.get(id, session)
        if not db_obj:
            return None
            
        await self._before_update(db_obj, obj_in, session, user_id)
        
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
            
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        
        await self._after_update(db_obj, session, user_id)
        return db_obj
    
    # Delete operations
    async def delete(self, id: ID, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """Permanently delete a record."""
        db_obj = await self.get(id, session)
        if not db_obj:
            return None
            
        await self._before_delete(db_obj, session, user_id)
        await session.delete(db_obj)
        await session.commit()
        await self._after_delete(db_obj, session, user_id)
        
        return db_obj
    
    async def soft_delete(self, id: ID, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """Soft delete a record by setting deleted_at timestamp."""
        db_obj = await self.get(id, session)
        if not db_obj or not hasattr(db_obj, "deleted_at"):
            return None
            
        await self._before_soft_delete(db_obj, session, user_id)
        
        db_obj.deleted_at = datetime.now(timezone.utc)
        if hasattr(db_obj, "deleted_by") and user_id is not None:
            db_obj.deleted_by = user_id
            
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        
        await self._after_soft_delete(db_obj, session, user_id)
        return db_obj
    
    async def restore(self, id: ID, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """Restore a soft-deleted record."""
        # Include deleted records in this query
        statement = select(self.model).where(getattr(self.model, "id") == id)
        result = await session.execute(statement)
        db_obj = result.scalars().first()
        
        if not db_obj or not hasattr(db_obj, "deleted_at"):
            return None
            
        db_obj.deleted_at = None
        db_obj.deleted_by = None
        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.now(timezone.utc)
        if hasattr(db_obj, "updated_by") and user_id is not None:
            db_obj.updated_by = user_id
            
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj
    
    # Helper methods
    async def _execute_paginated_query(self, query, session: AsyncSession, skip: int = 0, limit: int = 100) -> Page[T]:
        """Execute a query with pagination."""
        paginated_query = query.offset(skip).limit(limit)
        
        count_query = select(func.count()).select_from(query.alias())
        
        result = await session.execute(paginated_query)
        items = result.scalars().all()
        
        total_result = await session.execute(count_query)
        total = total_result.scalar_one_or_none() or 0
        
        return Page[T](
            items=items, 
            total=total, 
            page=(skip // limit) + 1 if limit > 0 else 1, 
            size=limit
        )
    
    # Event hooks - override these in your services
    async def _before_create(self, obj_in: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called before creating an object."""
        pass
    
    async def _after_create(self, obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called after creating an object."""
        pass
    
    async def _before_update(self, db_obj: T, obj_in: Dict[str, Any], session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called before updating an object."""
        pass
    
    async def _after_update(self, db_obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called after updating an object."""
        pass
    
    async def _before_delete(self, db_obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called before deleting an object."""
        pass
    
    async def _after_delete(self, db_obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called after deleting an object."""
        pass
    
    async def _before_soft_delete(self, db_obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called before soft-deleting an object."""
        pass
    
    async def _after_soft_delete(self, db_obj: T, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hook called after soft-deleting an object."""
        pass