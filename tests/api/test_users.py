import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

from app.core.config import settings
from app.schemas.user import UserCreate, UserRead # UserRead for response validation
from app.services.user_service import UserService

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, db_session: AsyncSession): # db_session not directly used, but client fixture uses it
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword"

    user_data = {"username": username, "email": email, "password": password}
    # Assuming public user creation endpoint for now.
    # If create_user_endpoint requires auth, this test would need to be adapted.
    response = await client.post(f"{settings.API_V1_STR}/users/", json=user_data)

    assert response.status_code == 201, response.text # Include response text on failure
    created_user_data = response.json()
    assert created_user_data["username"] == username
    assert created_user_data["email"] == email
    assert "id" in created_user_data
    assert "hashed_password" not in created_user_data
    assert "roles" in created_user_data # UserRead includes roles, should be empty list by default

@pytest.mark.asyncio
async def test_read_users_me_requires_auth(client: AsyncClient):
    response = await client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 401 # Unauthorized without token

@pytest.mark.asyncio
async def test_read_users_me_with_auth(client: AsyncClient, db_session: AsyncSession):
    user_service = UserService()
    username = f"me_user_{uuid.uuid4().hex[:6]}"
    email = f"me_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword"

    db_user = await user_service.get_user_by_username(username, db_session)
    if not db_user:
        user_in_create = UserCreate(username=username, email=email, password=password, is_active=True)
        db_user = await user_service.create_user(user_in_create, db_session)

    login_payload = {"username": username, "password": password}
    login_response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_payload)
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"{settings.API_V1_STR}/users/me", headers=headers)

    assert response.status_code == 200, response.text
    user_data = response.json()
    assert user_data["username"] == username
    assert user_data["email"] == email
    assert user_data["id"] == str(db_user.id)
    assert "roles" in user_data # Expect roles to be present (empty list if none assigned)

# TODO: Add more tests for:
# - GET /users/ (list users, with pagination, requires superuser)
# - GET /users/{user_id} (requires auth, specific user details)
# - PUT /users/{user_id} (update user, permissions check)
# - DELETE /users/{user_id} (delete user, superuser)
# - POST /users/{user_id}/roles/{role_id} (assign role, superuser)
# - DELETE /users/{user_id}/roles/{role_id} (revoke role, superuser)
# - Tests for non-superuser access attempts where superuser is required.
# - Tests for trying to update/delete other users as non-superuser.
# - Tests for input validation (e.g., invalid email, short password for UserCreate).
