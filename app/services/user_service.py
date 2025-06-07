import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlmodel import select, func
from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User # Ensures User is available for type hints
from app.models.role import Role
from app.models.associations import UserRole
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.schemas.common import Page
from app.core.security import get_password_hash # Needed for password reset
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class UserService:
    async def create_user(self, user_in: UserCreate, session: AsyncSession) -> User:
        logger.info(f"Attempting to create user: {user_in.username}")
        hashed_password = get_password_hash(user_in.password)
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
        logger.info(f"User {db_user.username} created successfully with ID: {db_user.id}")
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

        users_read = [UserRead.from_attributes(user) for user in users]
        return Page[UserRead](items=users_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_user(
        self, user_id: uuid.UUID, user_in: UserUpdate, session: AsyncSession
    ) -> Optional[User]:
        db_user = await session.get(User, user_id)
        if not db_user:
            logger.warning(f"Update user failed: User with ID {user_id} not found.")
            return None

        update_data = user_in.model_dump(exclude_unset=True)
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
        return db_user

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

    # --- Email Verification Methods ---
    async def _generate_secure_token(self, length: int = 32) -> str:
        # This can be reused for password reset tokens as well
        return secrets.token_urlsafe(length)

    async def _send_verification_email(self, user: User, token: str):
        logger.info(f"Simulating sending verification email to {user.email} for user {user.username}")
        logger.info(f"Verification token: {token}")
        logger.info(f"Verification link for API testing: http://localhost:8000{settings.API_V1_STR}/users/verify-email/{token}")

    async def request_email_verification(self, email: str, session: AsyncSession) -> tuple[bool, str]:
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
        user_db.email_verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=expire_hours)

        session.add(user_db)
        await session.commit()
        await session.refresh(user_db)

        await self._send_verification_email(user_db, token)
        logger.info(f"Email verification token generated for {user_db.email} (user {user_db.username}). Expires in {expire_hours} hours.")
        return True, "TOKEN_SENT"

    async def verify_email(self, token: str, session: AsyncSession) -> Optional[User]:
        logger.info(f"Attempting to verify email with token (prefix): {token[:10]}...")
        statement = select(User).where(User.email_verification_token == token)
        result = await session.exec(statement)
        user_db = result.first()

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

    # --- Password Reset Methods ---
    async def _send_password_reset_email(self, user: User, token: str):
        logger.info(f"Simulating sending password reset email to {user.email} for user {user.username}")
        logger.info(f"Password reset token: {token}")
        # The link should point to a frontend URL that then calls our API with the token
        # Example frontend link: f"http://yourfrontend.com/reset-password?token={token}"
        logger.info(f"Password reset link for API testing (token part): .../reset-password/{token} (actual endpoint takes token in body or path)")

    async def request_password_reset(self, email: str, session: AsyncSession) -> tuple[bool, str]:
        logger.info(f"Request for password reset received for: {email}")
        user = await self.get_user_by_email(email, session)
        if not user:
            logger.warning(f"Password reset request: User with email {email} not found.")
            return False, "USER_NOT_FOUND"

        # Optionally, check if user is active or if email is verified before allowing password reset
        # if not user.is_active:
        #     logger.warning(f"Password reset request for inactive user: {email}")
        #     return False, "USER_INACTIVE"
        # if not user.is_email_verified: # Often, password reset is allowed for unverified emails too
        #     logger.warning(f"Password reset request for unverified email: {email}")
        #     return False, "EMAIL_NOT_VERIFIED"

        token = await self._generate_secure_token() # Reusing the same token generator
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
        logger.info(f"Attempting to reset password with token (prefix): {token[:10]}...")
        statement = select(User).where(User.password_reset_token == token)
        result = await session.exec(statement)
        user = result.first()

        if not user:
            logger.warning(f"Password reset failed: Invalid token (prefix {token[:10]}...).")
            return False

        if user.password_reset_token != token: # Belt-and-suspenders
            logger.warning(f"Password reset failed for user {user.username}: Token mismatch.")
            return False

        if user.password_reset_token_expires_at is None or \
           user.password_reset_token_expires_at < datetime.now(timezone.utc):
            logger.warning(f"Password reset failed for user {user.username}: Token expired.")
            user.password_reset_token = None # Clear expired token
            user.password_reset_token_expires_at = None
            session.add(user)
            await session.commit()
            return False

        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None # Clear token after successful reset
        user.password_reset_token_expires_at = None
        # Optionally, force re-login by invalidating sessions if using session management beyond JWTs
        # Optionally, mark email as re-verified if password change implies control of email
        # user.is_email_verified = True
        session.add(user)
        await session.commit()
        logger.info(f"Password successfully reset for user: {user.username}")
        return True
