import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.associations import UserRole
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.schemas.common import Page
from app.core.security import get_password_hash

class UserService:
    async def create_user(self, user_in: UserCreate, session: AsyncSession) -> User:
        hashed_password = get_password_hash(user_in.password)
        # For SQLModel, direct instantiation is common and preferred
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=user_in.is_active if user_in.is_active is not None else True,
            is_superuser=user_in.is_superuser if user_in.is_superuser is not None else False,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user

    async def get_user(self, user_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        return await session.get(User, user_id)

    async def get_user_by_username(self, username: str, session: AsyncSession) -> Optional[User]:
        statement = select(User).where(User.username == username)
        result = await session.exec(statement)
        return result.first()

    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        return result.first()

    async def get_users(
        self, skip: int, limit: int, session: AsyncSession
    ) -> Page[UserRead]:
        statement = select(User).offset(skip).limit(limit)
        count_statement = select(func.count()).select_from(User)

        results = await session.exec(statement)
        users = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one()

        # Convert User models to UserRead schemas using Pydantic V2's from_attributes
        users_read = [UserRead.from_attributes(user) for user in users]

        return Page[UserRead](items=users_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_user(
        self, user_id: uuid.UUID, user_in: UserUpdate, session: AsyncSession
    ) -> Optional[User]:
        db_user = await session.get(User, user_id)
        if not db_user:
            return None

        update_data = user_in.model_dump(exclude_unset=True) # Pydantic V2
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data["password"])
            del update_data["password"]

        for key, value in update_data.items():
            setattr(db_user, key, value)

        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        db_user = await session.get(User, user_id)
        if not db_user:
            return None
        await session.delete(db_user)
        await session.commit()
        return db_user # User object is available but deleted from DB

    async def assign_role_to_user(self, user_id: uuid.UUID, role_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        user = await session.get(User, user_id)
        role = await session.get(Role, role_id)
        if not user or not role:
            return None

        existing_link_stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        existing_link_result = await session.exec(existing_link_stmt)
        if existing_link_result.first():
            await session.refresh(user)
            return user

        user_role_link = UserRole(user_id=user_id, role_id=role_id)
        session.add(user_role_link)
        await session.commit()
        await session.refresh(user)
        return user

    async def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        user = await session.get(User, user_id)
        if not user:
            return None

        statement = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        result = await session.exec(statement)
        user_role_link = result.first()

        if user_role_link:
            await session.delete(user_role_link)
            await session.commit()

        await session.refresh(user)
        return user
