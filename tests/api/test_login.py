import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.services.user_service import UserService # To create a user for testing login
from app.schemas.user import UserCreate

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, db_session: AsyncSession):
    # Create a test user directly via service
    user_service = UserService()
    test_username = "testloginuser"
    test_password = "testloginpass"
    # Use a unique email to avoid conflicts if tests run multiple times without DB cleanup
    test_email = "testlogin@example.com"

    # Check if user exists, if so, perhaps delete or use unique names
    existing_user = await user_service.get_user_by_username(test_username, db_session)
    if not existing_user:
        user_in = UserCreate(username=test_username, email=test_email, password=test_password, is_active=True)
        await user_service.create_user(user_in, db_session)
    # else: ensure existing user is active and has known password if reusing

    # Attempt login
    login_data = {"username": test_username, "password": test_password}
    # Ensure the prefix settings.API_V1_STR is used correctly
    response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    user_service = UserService()
    test_username = "testloginuserwp"
    test_password = "correctpassword"
    test_email = "testloginwp@example.com"

    existing_user = await user_service.get_user_by_username(test_username, db_session)
    if not existing_user:
        user_in = UserCreate(username=test_username, email=test_email, password=test_password, is_active=True)
        await user_service.create_user(user_in, db_session)

    login_data = {"username": test_username, "password": "wrongpassword"}
    response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert response.status_code == 401 # Unauthorized
    assert "Incorrect username or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    user_service = UserService()
    test_username = "testlogininactive"
    test_password = "password"
    test_email = "testinactive@example.com"

    existing_user = await user_service.get_user_by_username(test_username, db_session)
    if not existing_user:
        user_in = UserCreate(username=test_username, email=test_email, password=test_password, is_active=False)
        await user_service.create_user(user_in, db_session)
    # If user exists but is active, update to inactive for this test
    elif existing_user.is_active:
        # This requires an update method that can change is_active without password, etc.
        # For simplicity, we assume create_user sets it correctly.
        # A robust test suite might need to ensure the state or use a dedicated inactive user.
        pass # Assuming user is already inactive as per creation logic for this test run.

    login_data = {"username": test_username, "password": test_password}
    response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert response.status_code == 400 # Bad Request
    assert "Inactive user" in response.json()["detail"]
