import uuid
from typing import List, Optional

from sqlmodel import select, func # select and func are still used from SQLModel for query building
# The type hint for AsyncSession in services should match what get_session provides.
# If get_session provides sqlalchemy.ext.asyncio.AsyncSession, this is correct.
from sqlalchemy.ext.asyncio import AsyncSession # Explicitly using SQLAlchemy's AsyncSession for clarity

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionRead
from app.schemas.common import Page
from app.core.logging_config import get_logger
from app.models.associations import RolePermission

logger = get_logger(__name__)

class PermissionService:
    async def create_permission(self, permission_in: PermissionCreate, session: AsyncSession) -> Permission:
        logger.info(f"Creating permission: {permission_in.name}")
        db_permission = Permission(name=permission_in.name, description=permission_in.description)
        session.add(db_permission)
        await session.commit()
        await session.refresh(db_permission)
        logger.info(f"Permission '{db_permission.name}' created successfully with ID: {db_permission.id}")
        return db_permission

    async def get_permission(self, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Permission]:
        logger.debug(f"Fetching permission by ID: {permission_id}")
        permission = await session.get(Permission, permission_id)
        if not permission:
            logger.warning(f"Permission with ID {permission_id} not found.")
        return permission

    async def get_permission_by_name(self, name: str, session: AsyncSession) -> Optional[Permission]:
        logger.debug(f"Fetching permission by name: {name}")
        statement = select(Permission).where(Permission.name == name)
        result_proxy = await session.execute(statement) # Changed: execute instead of exec
        permission = result_proxy.scalars().first() # Changed: scalars().first()
        if not permission:
            logger.debug(f"Permission with name '{name}' not found.")
        return permission

    async def get_permissions(self, skip: int, limit: int, session: AsyncSession) -> Page[PermissionRead]:
        logger.debug(f"Fetching permissions: skip={skip}, limit={limit}")

        statement = select(Permission).offset(skip).limit(limit)
        count_statement = select(func.count(Permission.id)).select_from(Permission) # More explicit count

        permissions_result_proxy = await session.execute(statement) # Changed
        permissions = permissions_result_proxy.scalars().all() # Changed

        total_count_result_proxy = await session.execute(count_statement) # Changed
        total = total_count_result_proxy.scalar_one_or_none() or 0 # scalar_one_or_none() is safer for count if table could be empty

        permissions_read = [PermissionRead.model_validate(perm) for perm in permissions]
        logger.debug(f"Found {len(permissions_read)} permissions for current page, total {total}.")
        return Page[PermissionRead](items=permissions_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_permission(
        self, permission_id: uuid.UUID, permission_in: PermissionUpdate, session: AsyncSession
    ) -> Optional[Permission]:
        logger.info(f"Updating permission ID: {permission_id}")
        db_permission = await session.get(Permission, permission_id)
        if not db_permission:
            logger.warning(f"Update failed: Permission with ID {permission_id} not found.")
            return None

        update_data = permission_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_permission, key, value)

        session.add(db_permission)
        await session.commit()
        await session.refresh(db_permission)
        logger.info(f"Permission '{db_permission.name}' (ID: {db_permission.id}) updated.")
        return db_permission

 
    
    async def delete_permission(self, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Permission]:
        logger.info(f"Deleting permission ID: {permission_id}")
        db_permission = await session.get(Permission, permission_id)
        if not db_permission:
            logger.warning(f"Delete failed: Permission with ID {permission_id} not found.")
            return None
    
        # Delete all RolePermission associations for this permission
        await session.execute(
            RolePermission.__table__.delete().where(RolePermission.permission_id == permission_id)
        )
        await session.commit()
    
        await session.delete(db_permission)
        await session.commit()
        logger.info(f"Permission '{db_permission.name}' (ID: {db_permission.id}) deleted.")
        return db_permission
    

