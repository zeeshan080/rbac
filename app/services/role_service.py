import uuid
from typing import List, Optional

from sqlmodel import select, func # select and func are still used from SQLModel for query building
from sqlalchemy.ext.asyncio import AsyncSession # Explicitly using SQLAlchemy's AsyncSession

from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import RolePermission
from app.schemas.role import RoleCreate, RoleUpdate, RoleRead
from app.schemas.common import Page
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class RoleService:
    async def create_role(self, role_in: RoleCreate, session: AsyncSession) -> Role:
        logger.info(f"Creating role: {role_in.name}")
        db_role = Role(name=role_in.name, description=role_in.description)
        session.add(db_role)
        await session.commit()
        await session.refresh(db_role)
        logger.info(f"Role '{db_role.name}' created successfully with ID: {db_role.id}")
        return db_role

    async def get_role(self, role_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        logger.debug(f"Fetching role by ID: {role_id}")
        role = await session.get(Role, role_id)
        if not role:
            logger.warning(f"Role with ID {role_id} not found.")
        return role

    async def get_role_by_name(self, name: str, session: AsyncSession) -> Optional[Role]:
        logger.debug(f"Fetching role by name: {name}")
        statement = select(Role).where(Role.name == name)
        result_proxy = await session.execute(statement)
        role = result_proxy.scalars().first()
        if not role:
            logger.debug(f"Role with name '{name}' not found.")
        return role

    async def get_roles(self, skip: int, limit: int, session: AsyncSession) -> Page[RoleRead]:
        logger.debug(f"Fetching roles: skip={skip}, limit={limit}")

        statement = select(Role).offset(skip).limit(limit)
        count_statement = select(func.count(Role.id)).select_from(Role) # More explicit count

        roles_result_proxy = await session.execute(statement)
        roles = roles_result_proxy.scalars().all()

        total_count_result_proxy = await session.execute(count_statement)
        total = total_count_result_proxy.scalar_one_or_none() or 0

        roles_read = [RoleRead.from_attributes(role) for role in roles]
        logger.debug(f"Found {len(roles_read)} roles for current page, total {total}.")
        return Page[RoleRead](items=roles_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_role(
        self, role_id: uuid.UUID, role_in: RoleUpdate, session: AsyncSession
    ) -> Optional[Role]:
        logger.info(f"Updating role ID: {role_id}")
        db_role = await session.get(Role, role_id)
        if not db_role:
            logger.warning(f"Update failed: Role with ID {role_id} not found.")
            return None

        update_data = role_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_role, key, value)

        session.add(db_role)
        await session.commit()
        await session.refresh(db_role)
        logger.info(f"Role '{db_role.name}' (ID: {db_role.id}) updated.")
        return db_role

    async def delete_role(self, role_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        logger.info(f"Deleting role ID: {role_id}")
        db_role = await session.get(Role, role_id)
        if not db_role:
            logger.warning(f"Delete failed: Role with ID {role_id} not found.")
            return None

        # Consider checking if role is assigned to any users or has permissions before deletion
        # from app.models.associations import UserRole
        # user_role_check_stmt = select(func.count(UserRole.user_id)).where(UserRole.role_id == role_id)
        # perm_role_check_stmt = select(func.count(RolePermission.permission_id)).where(RolePermission.role_id == role_id)
        # user_count_proxy = await session.execute(user_role_check_stmt) # Changed
        # perm_count_proxy = await session.execute(perm_role_check_stmt) # Changed
        # if user_count_proxy.scalar_one() > 0 or perm_count_proxy.scalar_one() > 0: # Changed
        #     logger.error(f"Deletion failed: Role {role_id} is in use (assigned to users or has permissions).")
        #     return None

        await session.delete(db_role)
        await session.commit()
        logger.info(f"Role '{db_role.name}' (ID: {db_role.id}) deleted.")
        return db_role

    async def assign_permission_to_role(self, role_id: uuid.UUID, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        logger.info(f"Assigning permission {permission_id} to role {role_id}")
        role = await session.get(Role, role_id)
        permission = await session.get(Permission, permission_id)

        if not role:
            logger.warning(f"Cannot assign permission: Role {role_id} not found.")
            return None
        if not permission:
            logger.warning(f"Cannot assign permission: Permission {permission_id} not found.")
            return None

        existing_link_stmt = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        existing_link_result_proxy = await session.execute(existing_link_stmt)
        if existing_link_result_proxy.scalars().first():
            logger.info(f"Permission {permission_id} already assigned to role {role_id}. Refreshing role.")
            # await session.refresh(role) # Refresh might not be needed if just confirming link
            return role # Return role as is, link exists

        role_permission_link = RolePermission(role_id=role_id, permission_id=permission_id)
        session.add(role_permission_link)
        await session.commit()
        await session.refresh(role)
        logger.info(f"Permission {permission_id} successfully assigned to role {role_id}.")
        return role

    async def revoke_permission_from_role(self, role_id: uuid.UUID, permission_id: uuid.UUID, session: AsyncSession) -> Optional[Role]:
        logger.info(f"Revoking permission {permission_id} from role {role_id}")
        role = await session.get(Role, role_id)
        if not role:
            logger.warning(f"Cannot revoke permission: Role {role_id} not found.")
            return None

        statement = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        result_proxy = await session.execute(statement)
        role_permission_link = result_proxy.scalars().first()

        if role_permission_link:
            await session.delete(role_permission_link)
            await session.commit()
            logger.info(f"Permission {permission_id} successfully revoked from role {role_id}.")
        else:
            logger.info(f"Permission {permission_id} was not assigned to role {role_id}, no action taken.")

        await session.refresh(role) # Refresh role to reflect changes in its relationships if accessed later
        return role
