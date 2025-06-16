import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set, Dict, Any, Union, Type

from sqlmodel import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import UserRole, RolePermission
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.core.security import get_password_hash
from app.core.logging_config import get_logger
from app.core.config import settings
from app.services.servicemixin import CRUDMixin

logger = get_logger(__name__)



class UserService(CRUDMixin[User]):
    """Service for managing users with CRUD operations and additional features."""
    model = User
    
    # === Override CRUD Mixin Hooks ===
    
    async def _before_create(self, obj_in: UserCreate, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Hash the password and set audit fields before creating a user."""
        #log the obj_in for debugging
        logger.debug(f"Creating user with input: {obj_in.model_dump()}")
        # Check if email or username already exists
        existing_user = await self.get_user_by_email(obj_in.email, session)
        if existing_user:
            logger.error(f"Email {obj_in.email} is already taken by another user.")
            raise ValueError(f"Email {obj_in.email} is already taken.")
        existing_user = await self.get_user_by_username(obj_in.username, session)
        if existing_user:
            logger.error(f"Username {obj_in.username} is already taken by another user.")
            raise ValueError(f"Username {obj_in.username} is already taken.")
        #check if user trying to create a superuser without permission and is not a superuser
        if obj_in.is_superuser and (not user_id or not await self.is_superuser(user_id, session)):
            logger.error("Attempt to create a superuser without permission.")
            raise ValueError("You do not have permission to create a superuser.")
        
        # Convert UserCreate (Pydantic model) to User (SQLModel/ORM model)
        user_obj : User = User(**obj_in.model_dump())

        if user_id:
            user_obj.created_by = user_id
            user_obj.created_at = datetime.now()

        if hasattr(obj_in, "password") and obj_in.password:
            user_obj.hashed_password = get_password_hash(obj_in.password)
        
        obj_in = user_obj
        logger.info(f"Preparing to create user: {getattr(obj_in, 'username', 'unknown')}")
        return obj_in  # Return the modified object for further processing
            
    async def _after_create(self, obj: User, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Reload the user with roles after creation."""
        statement = select(User).options(selectinload(User.roles).selectinload(Role.permissions)).where(User.id == obj.id)
        result = await session.execute(statement)
        user_with_roles = result.scalars().first()
        
        # Copy attributes to ensure obj has all relationships loaded
        for attr, value in vars(user_with_roles).items():
            if not attr.startswith('_'):
                setattr(obj, attr, value)
        
        logger.info(f"User {obj.username} created successfully with ID: {obj.id}")
    
    async def _before_update(self, db_obj: User, obj_in: UserUpdate, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """set audit fields before updating a user."""
        if hasattr(obj_in, "email") and obj_in.email:
            existing_user = await self.get_user_by_email(obj_in.email, session)
            if existing_user and existing_user.id != db_obj.id:
                logger.error(f"Email {obj_in.email} is already taken by another user.")
                raise ValueError(f"Email {obj_in.email} is already taken.")
        if hasattr(obj_in, "username") and obj_in.username:
            existing_user = await self.get_user_by_username(obj_in.username, session)
            if existing_user and existing_user.id != db_obj.id:
                logger.error(f"Username {obj_in.username} is already taken by another user.")
                raise ValueError(f"Username {obj_in.username} is already taken.")
        # Check if user trying to update a superuser without permission and is not a superuser
        if (hasattr(obj_in, "is_superuser") and obj_in.is_superuser) and (not user_id or not await self.is_superuser(user_id, session)):
            logger.error("Attempt to update a user to superuser without permission.")
            raise ValueError("You do not have permission to update a user to superuser.")
        
            
        if user_id:
            db_obj.updated_by = user_id
            db_obj.updated_at = datetime.now()
        logger.info(f"Updating user: {db_obj.username} (ID: {db_obj.id})")
    
    async def _after_update(self, db_obj: User, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Reload the user with roles after update."""
        statement = select(User).options(selectinload(User.roles).selectinload(Role.permissions)).where(User.id == db_obj.id)
        result = await session.execute(statement)
        user_with_roles = result.scalars().first()
        
        # Copy attributes to ensure db_obj has all relationships loaded
        for attr, value in vars(user_with_roles).items():
            if not attr.startswith('_'):
                setattr(db_obj, attr, value)
        
        logger.info(f"User {db_obj.username} updated successfully")
    
    async def _before_delete(self, db_obj: User, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Delete all UserRole associations before deleting the user."""
        logger.info(f"Preparing to delete user: {db_obj.username} (ID: {db_obj.id})")
        await session.execute(
            UserRole.__table__.delete().where(UserRole.user_id == db_obj.id)
        )
        await session.commit()
        logger.info(f"Removed all role associations for user: {db_obj.id}")
    
    async def _after_delete(self, db_obj: User, session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> None:
        """Log after user deletion."""
        logger.info(f"User {db_obj.username} (ID: {db_obj.id}) deleted successfully")
    
    # === Custom Methods Not Covered by CRUDMixin ===
    
    # -- Role Management Methods --
    
    async def create_user_with_roles(self, user_in: UserCreate, role_ids: List[uuid.UUID], session: AsyncSession, user_id: Optional[uuid.UUID] = None) -> Optional[User]:
        """Create a user and assign the given roles."""
        logger.info(f"Creating user {user_in.username} with roles: {role_ids}")
        
        # Use CRUDMixin create method via dict to leverage the hooks
        user_dict = user_in.model_dump()
        user = await self.create(user_dict, session, user_id)
        
        # Assign roles
        for role_id in role_ids:
            await self.assign_role_to_user(user.id, role_id, session)
            
        return user
        
    async def assign_role_to_user(self, user_id: uuid.UUID, role_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        """Assign a role to a user."""
        logger.info(f"Assigning role {role_id} to user {user_id}")
        user = await self.get(user_id, session)
        role = await session.get(Role, role_id)
    
        if not user:
            logger.warning(f"Cannot assign role: User {user_id} not found.")
            return None
        if not role:
            logger.warning(f"Cannot assign role: Role {role_id} not found.")
            return None
    
        existing_link_stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        existing_link_result_proxy = await session.execute(existing_link_stmt)
        if existing_link_result_proxy.scalars().first():
            logger.info(f"Role {role_id} already assigned to user {user_id}.")
        else:
            user_role_link = UserRole(user_id=user_id, role_id=role_id)
            session.add(user_role_link)
            await session.commit()
            logger.info(f"Role {role_id} assigned to user {user_id}.")
    
        # Return the updated user with roles
        return await self.get(user_id, session)
    
    async def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        """Revoke a role from a user."""
        logger.info(f"Revoking role {role_id} from user {user_id}")
        user = await self.get(user_id, session)
        if not user:
            logger.warning(f"Cannot revoke role: User {user_id} not found.")
            return None
    
        # Find the UserRole association
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result_proxy = await session.execute(statement)
        user_role_link = result_proxy.scalars().first()
    
        if user_role_link:
            await session.delete(user_role_link)
            await session.commit()
            logger.info(f"Role {role_id} revoked from user {user_id}.")
        else:
            logger.info(f"Role {role_id} was not assigned to user {user_id}.")
    
        # Return the updated user with roles
        return await self.get(user_id, session)
    
    # -- Helper Methods for Finding Users --
    
    async def get_user_by_username(self, username: str, session: AsyncSession) -> Optional[User]:
        """Get a user by username with roles and permissions loaded."""
        logger.debug(f"Fetching user by username: {username}")
        return await self.get_by_field("username", username, session)
    
    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        """Get a user by email with roles and permissions loaded."""
        logger.debug(f"Fetching user by email: {email}")
        return await self.get_by_field("email", email, session)
    
    # Override to ensure roles are always loaded
    async def get(self, id: uuid.UUID, session: AsyncSession) -> Optional[User]:
        """Get a user by ID with roles and permissions loaded."""
        statement = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.id == id)
        result = await session.execute(statement)
        return result.scalars().first()
    
    async def get_by_field(self, field_name: str, value: Any, session: AsyncSession) -> Optional[User]:
        """Get a user by a specific field value with roles and permissions loaded."""
        statement = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(getattr(User, field_name) == value)
        result = await session.execute(statement)
        return result.scalars().first()
    
    async def filter_and_search(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True,
        search_term: Optional[str] = None,
        search_field: Optional[str] = None,
        filter_param: Optional[str] = None,
    ) -> Page[User]:
        """
        Single method to filter and/or search with ordering, pagination, and role filtering.
        - `search_term` & `search_fields` apply OR-based searching (partial match on string columns).
        - `filters` apply exact matching (e.g. username=..., is_superuser=..., etc.).
        - Combine both for a flexible query.
        """
        query = select(self.model)
        conditions = []
        #append search conditions if search_term and search_field are provided
        if search_term and search_field:
            if hasattr(self.model, search_field):
                column = getattr(self.model, search_field)
                conditions.append(column.ilike(f"%{search_term}%"))
            else:
                logger.warning(f"Search field {search_field} does not exist on model {self.model.__name__}")
        
        # 1) Handle filter only 1 parameter
        if filter_param:
            if hasattr(self.model, filter_param):
                column = getattr(self.model, filter_param)
                conditions.append(column.is_(True))

        # 4) Combine conditions
        if conditions:
            query = query.where(and_(*conditions))

        # 6) Handle soft-deletes
        if hasattr(self.model, "deleted_at"):
            query = query.where(getattr(self.model, "deleted_at").is_(None))

        # 7) Sort results
        if hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            if order_desc:
                column = column.desc()
            query = query.order_by(column)

        # 8) Eager-load roles & permissions
        query = query.options(
            selectinload(User.roles).selectinload(Role.permissions)
        )

        # 9) Return paginated result
        return await self._execute_paginated_query(query, session, skip, limit)
    # -- Email Verification Methods --
    
    async def _generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure token for email verification or password reset."""
        return secrets.token_urlsafe(length)

    async def _send_verification_email(self, user: User, token: str):
        """Simulate sending a verification email."""
        logger.info(f"Simulating sending verification email to {user.email} for user {user.username}")
        logger.info(f"Verification token: {token}")
        logger.info(f"Verification link for API testing: http://localhost:8000{settings.API_V1_STR}/users/verify-email/{token}")

    async def request_email_verification(self, email: str, session: AsyncSession) -> tuple[bool, str]:
        """Request email verification for a user."""
        logger.info(f"Request for email verification received for: {email}")
        user_db = await self.get_user_by_email(email, session)
        if not user_db:
            logger.warning(f"Email verification request: User with email {email} not found.")
            return False, "USER_NOT_FOUND"

        if user_db.is_email_verified:
            logger.info(f"Email {email} is already verified for user {user_db.username}.")
            return True, "ALREADY_VERIFIED"

        token = await self._generate_secure_token()
        user_db.email_verification_token = token
        expire_hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
        user_db.email_verification_token_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=expire_hours)

        session.add(user_db)
        await session.commit()
        await session.refresh(user_db)

        await self._send_verification_email(user_db, token)
        logger.info(f"Email verification token generated for {user_db.email} (user {user_db.username}). Expires in {expire_hours} hours.")
        return True, "TOKEN_SENT"

    async def verify_email(self, token: str, session: AsyncSession) -> Optional[User]:
        """Verify a user's email with token."""
        logger.info(f"Attempting to verify email with token (prefix): {token[:10]}...")
        statement = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.email_verification_token == token)
        result_proxy = await session.execute(statement)
        user_db = result_proxy.scalars().first()

        if not user_db:
            logger.warning(f"Email verification failed: Invalid token (prefix {token[:10]}...).")
            return None

        if user_db.email_verification_token != token:
             logger.warning(f"Email verification failed for user {user_db.username}: Token mismatch.")
             return None

        if user_db.is_email_verified:
            logger.info(f"Email for user {user_db.username} is already verified. Clearing token.")
            user_db.email_verification_token = None
            user_db.email_verification_token_expires_at = None
            session.add(user_db)
            await session.commit()
            return user_db

        if user_db.email_verification_token_expires_at is None or \
           user_db.email_verification_token_expires_at < datetime.now(timezone.utc):
            logger.warning(f"Email verification failed for user {user_db.username}: Token expired.")
            user_db.email_verification_token = None
            user_db.email_verification_token_expires_at = None
            session.add(user_db)
            await session.commit()
            return None

        user_db.is_email_verified = True
        user_db.email_verification_token = None
        user_db.email_verification_token_expires_at = None
        session.add(user_db)
        await session.commit()
        await session.refresh(user_db)
        logger.info(f"Email successfully verified for user: {user_db.username}")
        return user_db

    # -- Password Reset Methods --
    
    async def _send_password_reset_email(self, user: User, token: str):
        """Simulate sending a password reset email."""
        logger.info(f"Simulating sending password reset email to {user.email} for user {user.username}")
        logger.info(f"Password reset token: {token}")
        logger.info(f"Password reset link for API testing (token part): .../reset-password/{token}")

    async def request_password_reset(self, email: str, session: AsyncSession) -> tuple[bool, str]:
        """Request password reset for a user."""
        logger.info(f"Request for password reset received for: {email}")
        user = await self.get_user_by_email(email, session)
        if not user:
            logger.warning(f"Password reset request: User with email {email} not found.")
            return False, "USER_NOT_FOUND"

        token = await self._generate_secure_token()
        user.password_reset_token = token
        expire_hours = settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
        user.password_reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=expire_hours)

        session.add(user)
        await session.commit()
        await session.refresh(user)

        await self._send_password_reset_email(user, token)
        logger.info(f"Password reset token generated for {user.email}. Expires in {expire_hours} hours.")
        return True, "TOKEN_SENT"

    async def reset_password_with_token(self, token: str, new_password: str, session: AsyncSession) -> bool:
        """Reset a user's password using a token."""
        logger.info(f"Attempting to reset password with token (prefix): {token[:10]}...")
        statement = select(User).where(User.password_reset_token == token)
        result_proxy = await session.execute(statement)
        user = result_proxy.scalars().first()

        if not user:
            logger.warning(f"Password reset failed: Invalid token (prefix {token[:10]}...).")
            return False

        if user.password_reset_token != token:
            logger.warning(f"Password reset failed for user {user.username}: Token mismatch.")
            return False

        if user.password_reset_token_expires_at is None or \
           user.password_reset_token_expires_at < datetime.now(timezone.utc):
            logger.warning(f"Password reset failed for user {user.username}: Token expired.")
            user.password_reset_token = None
            user.password_reset_token_expires_at = None
            session.add(user)
            await session.commit()
            return False

        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        session.add(user)
        await session.commit()
        logger.info(f"Password successfully reset for user: {user.username}")
        return True

    # -- Permission Methods --
    
    async def get_user_permission_names(self, user: User, session: AsyncSession) -> Set[str]:
        """Get a set of permission names for a user."""
        logger.debug(f"Fetching permission names for user: {user.username} (ID: {user.id})")
        stmt = (
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(Role, RolePermission.role_id == Role.id)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )

        permission_results_proxy = await session.execute(stmt)
        permission_names: Set[str] = set(permission_results_proxy.scalars().all())

        logger.debug(f"Permissions for {user.username}: {permission_names}")
        return permission_names