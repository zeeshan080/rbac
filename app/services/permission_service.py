import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionRead
from app.schemas.common import Page

class PermissionService:
    async def create_permission(self, permission_in: PermissionCreate, session: AsyncSession) -> Permission:
        # For SQLModel, direct instantiation from schema data is common
        db_permission = Permission(name=permission_in.name, description=permission_in.description)
        session.add(db_permission)
        await session.commit()
        await session.refresh(db_permission)
        return db_permission

    async def get_permission(self, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Permission]:
        return await session.get(Permission, permission_id)

    async def get_permission_by_name(self, name: str, session: AsyncSession) -> Optional[Permission]:
        statement = select(Permission).where(Permission.name == name)
        result = await session.exec(statement)
        return result.first()

    async def get_permissions(self, skip: int, limit: int, session: AsyncSession) -> Page[PermissionRead]:
        statement = select(Permission).offset(skip).limit(limit)
        count_statement = select(func.count()).select_from(Permission)

        results = await session.exec(statement)
        permissions = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one()

        # Convert Permission models to PermissionRead schemas using Pydantic V2's from_attributes
        permissions_read = [PermissionRead.from_attributes(perm) for perm in permissions]
        return Page[PermissionRead](items=permissions_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_permission(
        self, permission_id: uuid.UUID, permission_in: PermissionUpdate, session: AsyncSession
    ) -> Optional[Permission]:
        db_permission = await session.get(Permission, permission_id)
        if not db_permission:
            return None

        update_data = permission_in.model_dump(exclude_unset=True) # Pydantic V2
        for key, value in update_data.items():
            setattr(db_permission, key, value)

        session.add(db_permission)
        await session.commit()
        await session.refresh(db_permission)
        return db_permission

    async def delete_permission(self, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Permission]:
        db_permission = await session.get(Permission, permission_id)
        if not db_permission:
            return None
        await session.delete(db_permission)
        await session.commit()
        return db_permission
