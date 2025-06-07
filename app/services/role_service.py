import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import RolePermission
from app.schemas.role import RoleCreate, RoleUpdate, RoleRead
from app.schemas.common import Page

class RoleService:
    async def create_role(self, role_in: RoleCreate, session: AsyncSession) -> Role:
        # For SQLModel, direct instantiation from schema data is common
        db_role = Role(name=role_in.name, description=role_in.description)
        session.add(db_role)
        await session.commit()
        await session.refresh(db_role)
        return db_role

    async def get_role(self, role_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        return await session.get(Role, role_id)

    async def get_role_by_name(self, name: str, session: AsyncSession) -> Optional[Role]:
        statement = select(Role).where(Role.name == name)
        result = await session.exec(statement)
        return result.first()

    async def get_roles(self, skip: int, limit: int, session: AsyncSession) -> Page[RoleRead]:
        statement = select(Role).offset(skip).limit(limit)
        count_statement = select(func.count()).select_from(Role)

        results = await session.exec(statement)
        roles = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one()

        # Convert Role models to RoleRead schemas using Pydantic V2's from_attributes
        roles_read = [RoleRead.from_attributes(role) for role in roles]
        return Page[RoleRead](items=roles_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_role(
        self, role_id: uuid.UUID, role_in: RoleUpdate, session: AsyncSession
    ) -> Optional[Role]:
        db_role = await session.get(Role, role_id)
        if not db_role:
            return None

        update_data = role_in.model_dump(exclude_unset=True) # Pydantic V2
        for key, value in update_data.items():
            setattr(db_role, key, value)

        session.add(db_role)
        await session.commit()
        await session.refresh(db_role)
        return db_role

    async def delete_role(self, role_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        db_role = await session.get(Role, role_id)
        if not db_role:
            return None
        await session.delete(db_role)
        await session.commit()
        return db_role

    async def assign_permission_to_role(self, role_id: uuid.UUID, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        role = await session.get(Role, role_id)
        permission = await session.get(Permission, permission_id)
        if not role or not permission:
            return None

        existing_link_stmt = select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
        existing_link_result = await session.exec(existing_link_stmt)
        if existing_link_result.first():
            await session.refresh(role)
            return role

        role_permission_link = RolePermission(role_id=role_id, permission_id=permission_id)
        session.add(role_permission_link)
        await session.commit()
        await session.refresh(role)
        return role

    async def revoke_permission_from_role(self, role_id: uuid.UUID, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        role = await session.get(Role, role_id)
        if not role:
            return None

        statement = select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
        result = await session.exec(statement)
        role_permission_link = result.first()

        if role_permission_link:
            await session.delete(role_permission_link)
            await session.commit()

        await session.refresh(role)
        return role
