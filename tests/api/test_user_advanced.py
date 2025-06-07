import pytest
import asyncio # For asyncio.sleep
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.user_service import UserService # To interact with user directly for setup/assertions
from app.schemas.user import UserCreate, UserRead
from app.models.user import User # For direct model interaction/assertions
from app.schemas.auth import PasswordResetRequestSchema, NewPasswordSchema # For password reset
# Import EmailVerificationRequest from where it's defined (currently in users router)
# This is a bit of an architectural smell; ideally, request models are also in schemas.
# For now, follow the existing structure. If users router defines it, import from there.
# Assuming it's `from app.routers.users import EmailVerificationRequest`
from app.routers.users import EmailVerificationRequest

# Helper to get a user directly from DB for assertions (bypassing service cache if any)
async def get_user_from_db(session: AsyncSession, email: Optional[str] = None, user_id: Optional[uuid.UUID] = None) -> Optional[User]:
    if user_id:
        return await session.get(User, user_id)
    if email:
        from sqlmodel import select # Local import to avoid top-level if only used here
        statement = select(User).where(User.email == email)
        results = await session.exec(statement)
        return results.first()
    return None

@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient, db_session: AsyncSession, user_service: UserService): # Added user_service fixture
    unique_email = f"verify_{uuid.uuid4().hex[:6]}@example.com"
    password = "password123"

    # 1. Create a new user
    user_create_payload = UserCreate(username=f"verifyuser_{uuid.uuid4().hex[:6]}", email=unique_email, password=password)
    # Use the user_service fixture instance
    created_user_model = await user_service.create_user(user_create_payload, db_session)
    assert created_user_model is not None
    assert not created_user_model.is_email_verified

    # 2. Request email verification
    req_ver_payload = EmailVerificationRequest(email=unique_email)
    response = await client.post(f"{settings.API_V1_STR}/users/request-verification-email", json=req_ver_payload.model_dump())
    assert response.status_code == 202 # Accepted
    assert response.json()["message"] == "If an account with this email exists and is not yet verified, a verification email process has been initiated."

    # 3. Retrieve the token (from DB, since email is mocked)
    user_in_db = await get_user_from_db(db_session, email=unique_email)
    assert user_in_db is not None
    assert user_in_db.email_verification_token is not None
    verification_token = user_in_db.email_verification_token
    assert user_in_db.email_verification_token_expires_at is not None
    assert user_in_db.email_verification_token_expires_at > datetime.now(timezone.utc)

    # 4. Verify email with the token
    response_verify = await client.get(f"{settings.API_V1_STR}/users/verify-email/{verification_token}")
    assert response_verify.status_code == 200, response_verify.text
    verified_user_data = UserRead(**response_verify.json())
    assert verified_user_data.email == unique_email
    assert verified_user_data.is_email_verified is True

    # 5. Check DB that token is cleared and user is verified
    user_in_db_after_verify = await get_user_from_db(db_session, email=unique_email)
    assert user_in_db_after_verify is not None
    assert user_in_db_after_verify.is_email_verified is True
    assert user_in_db_after_verify.email_verification_token is None
    assert user_in_db_after_verify.email_verification_token_expires_at is None

    # 6. Test verifying with an invalid token
    response_invalid_token = await client.get(f"{settings.API_V1_STR}/users/verify-email/invalidtoken123")
    assert response_invalid_token.status_code == 400
    assert "Invalid, expired, or already used verification token" in response_invalid_token.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, db_session: AsyncSession, user_service: UserService): # Added user_service fixture
    unique_email = f"reset_{uuid.uuid4().hex[:6]}@example.com"
    username = f"resetuser_{uuid.uuid4().hex[:6]}"
    original_password = "originalPassword123"
    new_password = "newStrongPassword456"

    # 1. Create user
    user_create = UserCreate(username=username, email=unique_email, password=original_password)
    await user_service.create_user(user_create, db_session)

    # 2. Request password reset
    req_reset_payload = PasswordResetRequestSchema(email=unique_email)
    response = await client.post(f"{settings.API_V1_STR}/users/request-password-reset", json=req_reset_payload.model_dump())
    assert response.status_code == 202
    assert response.json()["message"] == "If an account with this email exists, a password reset link has been sent."

    # 3. Retrieve token from DB
    user_in_db = await get_user_from_db(db_session, email=unique_email)
    assert user_in_db is not None
    assert user_in_db.password_reset_token is not None
    reset_token = user_in_db.password_reset_token

    # 4. Reset password with token
    reset_payload = NewPasswordSchema(token=reset_token, new_password=new_password)
    response_reset = await client.post(f"{settings.API_V1_STR}/users/reset-password", json=reset_payload.model_dump())
    assert response_reset.status_code == 200, response_reset.text
    assert response_reset.json()["message"] == "Password has been reset successfully."

    # 5. Verify token is cleared in DB
    user_in_db_after = await get_user_from_db(db_session, email=unique_email)
    assert user_in_db_after is not None
    assert user_in_db_after.password_reset_token is None

    # 6. Try to login with new password
    login_payload = {"username": username, "password": new_password}
    response_login = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_payload)
    assert response_login.status_code == 200, response_login.text
    assert "access_token" in response_login.json()

    # 7. Try to login with old password (should fail)
    login_payload_old_pw = {"username": username, "password": original_password}
    response_login_old = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_payload_old_pw)
    assert response_login_old.status_code == 401 # Unauthorized


@pytest.mark.asyncio
async def test_account_lockout(client: AsyncClient, db_session: AsyncSession, user_service: UserService): # Added user_service fixture
    unique_email = f"lockout_{uuid.uuid4().hex[:6]}@example.com"
    username = f"lockoutuser_{uuid.uuid4().hex[:6]}"
    password = "password123"

    # 1. Create user
    user_create = UserCreate(username=username, email=unique_email, password=password)
    await user_service.create_user(user_create, db_session)

    # 2. Fail login attempts to lock account
    login_payload_fail = {"username": username, "password": "wrongpassword"}
    for i in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_payload_fail)
        assert response.status_code == 401, response.text # Incorrect username or password
        user_db_check = await get_user_from_db(db_session, email=unique_email)
        assert user_db_check is not None
        assert user_db_check.failed_login_attempts == (i + 1)
        if i < settings.MAX_FAILED_LOGIN_ATTEMPTS -1: # Check not locked before final attempt
             assert user_db_check.is_locked_out is False

    # 3. Next attempt should result in account locked
    response_locked = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_payload_fail)
    assert response_locked.status_code == 403, response_locked.text # Account locked
    assert "Account locked" in response_locked.json()["detail"]

    user_db_locked = await get_user_from_db(db_session, email=unique_email)
    assert user_db_locked is not None
    assert user_db_locked.is_locked_out is True
    assert user_db_locked.failed_login_attempts == settings.MAX_FAILED_LOGIN_ATTEMPTS
    assert user_db_locked.lockout_until is not None
    assert user_db_locked.lockout_until > datetime.now(timezone.utc)

    # Optional: Test that account unlocks after duration
    # This requires either time manipulation (e.g., with freezegun) or actual waiting.
    # For an automated test without time manipulation, you'd typically set a very short lockout duration
    # in settings for the test environment and then asyncio.sleep for that duration.
    # Example (if ACCOUNT_LOCKOUT_DURATION_MINUTES was, say, 0.01 for testing):
    # await asyncio.sleep(settings.ACCOUNT_LOCKOUT_DURATION_MINUTES * 60 + 1) # Wait for lockout to expire + buffer
    # response_after_lockout_correct_pw = await client.post(f"{settings.API_V1_STR}/login/access-token", data={"username": username, "password": password})
    # assert response_after_lockout_correct_pw.status_code == 200, response_after_lockout_correct_pw.text
    # user_db_unlocked = await get_user_from_db(db_session, email=unique_email)
    # assert user_db_unlocked is not None
    # assert user_db_unlocked.is_locked_out is False
    # assert user_db_unlocked.failed_login_attempts == 0
