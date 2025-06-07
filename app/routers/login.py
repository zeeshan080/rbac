from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timedelta, timezone # Added for lockout logic

from app.core.config import settings # Added for lockout settings
from app.core.security import create_access_token, verify_password
from app.core.dependencies import get_current_active_user
from app.services.user_service import UserService
from app.schemas.token import Token
from app.schemas.user import UserRead # Ensure UserRead is available for test_token
from app.database import get_session
from app.models.user import User # Ensure User model is available
from app.core.logging_config import get_logger # Added for logging

logger = get_logger(__name__) # Added

router = APIRouter()

@router.post("/access-token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_service: Annotated[UserService, Depends(UserService)]
):
    logger.info(f"Login attempt for username: {form_data.username}")
    user = await user_service.get_user_by_username(username=form_data.username, session=session)

    if user:
        # Check for account lockout
        if user.is_locked_out:
            if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
                logger.warning(f"Login attempt for locked account: {form_data.username}. Lockout until: {user.lockout_until}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, # Changed from 401 to 403 for locked
                    detail=f"Account locked due to too many failed login attempts. Try again later.",
                )
            else:
                # Lockout period has expired, reset lockout status before proceeding with login attempt
                logger.info(f"Lockout period expired for user: {form_data.username}. Resetting lockout status.")
                user.is_locked_out = False
                user.failed_login_attempts = 0
                user.lockout_until = None
                session.add(user) # Add to session to track changes
                # We will commit either on failed attempt or successful login below

    if not user or not verify_password(form_data.password, user.hashed_password):
        if user: # User exists, but password was incorrect
            user.failed_login_attempts += 1
            logger.warning(f"Failed login attempt for user: {form_data.username}. Attempt #{user.failed_login_attempts} of {settings.MAX_FAILED_LOGIN_ATTEMPTS}.")
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS and not user.is_locked_out: # Lock only if not already (e.g. expired but failed again)
                user.is_locked_out = True
                user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                logger.error(f"Account for user {form_data.username} locked until {user.lockout_until} due to {user.failed_login_attempts} failed attempts.")
            session.add(user)
            await session.commit()
        else: # User does not exist
            logger.warning(f"Failed login attempt: Username {form_data.username} not found.")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active: # Check after successful password verification
        logger.warning(f"Login attempt for inactive user: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    # If login is successful, reset failed attempts and lockout status if they were set
    if user.failed_login_attempts > 0 or user.is_locked_out: # is_locked_out check is redundant if lockout expired and was reset
        logger.info(f"Successful login for user: {form_data.username}. Resetting failed attempts and lockout status.")
        user.failed_login_attempts = 0
        user.is_locked_out = False
        user.lockout_until = None
        session.add(user)
        await session.commit() # Commit these changes

    access_token = create_access_token(subject=str(user.id))
    logger.info(f"Access token generated for user: {form_data.username}")
    return Token(access_token=access_token, token_type="bearer")

@router.get("/test-token", response_model=UserRead)
async def test_token(current_user: Annotated[User, Depends(get_current_active_user)]):
    return UserRead.from_attributes(current_user)
