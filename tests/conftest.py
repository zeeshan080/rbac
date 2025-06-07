import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator, List, Set, Tuple # Added List, Set, Tuple

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from app.main import app as main_app
from app.core.config import settings
from app.database import get_session
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import UserRole, RolePermission
from app.schemas.user import UserCreate
from app.schemas.role import RoleCreate
from app.schemas.permission import PermissionCreate
from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.core.security import create_access_token # For getting tokens for test users

import os
import uuid
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode # For SSL handling

# Determine Test Database URL
TEST_DATABASE_URL_STR = os.getenv("DATABASE_URL_TEST", settings.DATABASE_URL_TEST)
USING_MAIN_DB_FOR_TESTS = False
if not TEST_DATABASE_URL_STR:
    TEST_DATABASE_URL_STR = str(settings.DATABASE_URL)
    USING_MAIN_DB_FOR_TESTS = True
    print(f"WARNING: DATABASE_URL_TEST not set. Falling back to main DATABASE_URL: {TEST_DATABASE_URL_STR}")
else:
    if TEST_DATABASE_URL_STR.startswith("postgresql://"):
        TEST_DATABASE_URL_STR = TEST_DATABASE_URL_STR.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"Using dedicated test database: {TEST_DATABASE_URL_STR}")

# SSL Handling for test_engine
parsed_test_url = urlparse(TEST_DATABASE_URL_STR)
test_query_params = parse_qs(parsed_test_url.query)
test_connect_args = {}
# Reconstruct query string without sslmode, if present
new_query = {k: v for k, v in test_query_params.items() if k.lower() != 'sslmode'}
if 'sslmode' in (key.lower() for key in test_query_params.keys()): # Check if sslmode was present
    if test_query_params.get('sslmode',[''])[0] == 'require': # Check its value
        test_connect_args["ssl"] = True

reconstructed_query_string = urlencode(new_query, doseq=True)
test_db_url_for_engine = urlunparse(parsed_test_url._replace(query=reconstructed_query_string))

test_engine = create_async_engine(test_db_url_for_engine, echo=False, connect_args=test_connect_args)
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

def run_alembic_migrations_programmatically(database_url: str, alembic_ini_path: str = "alembic.ini"):
    print(f"Running Alembic migrations on: {'MAIN DB (used as test DB)' if USING_MAIN_DB_FOR_TESTS else database_url}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    # Alembic's env.py uses settings.DATABASE_URL. For tests, we must ensure it points to the test DB.
    # The most reliable way is to set an environment variable that env.py can read for the test DB URL.
    # Forcing sqlalchemy.url here is direct for this programmatic call.
    # Ensure the URL for Alembic's sync operations doesn't have asyncpg specific connect_args in its query part.
    # The URL for Alembic should be the one that its sync `create_engine` can handle.
    # Our env.py's online mode is async, but Alembic CLI operations might use offline or sync paths.

    # Use the original TEST_DATABASE_URL_STR for Alembic config, as our env.py is designed to parse it.
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL_STR)

    print("Upgrading database to head...")
    alembic_command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied.")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if USING_MAIN_DB_FOR_TESTS:
        print("WARNING: Running migrations on MAIN database. This is risky for production data.")
    try:
        run_alembic_migrations_programmatically(TEST_DATABASE_URL_STR)
    except Exception as e:
        print(f"Error during Alembic migration for test setup: {e}")
        pytest.exit(f"Failed to set up test database with migrations: {e}", 1)
    yield

@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.close()

@pytest.fixture()
def test_app_instance(db_session: AsyncSession) -> Generator[FastAPI, None, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    original_overrides = main_app.dependency_overrides.copy()
    main_app.dependency_overrides[get_session] = override_get_session
    yield main_app
    main_app.dependency_overrides = original_overrides

@pytest_asyncio.fixture()
async def client(test_app_instance: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(app=test_app_instance, base_url="http://testserver") as c:
        yield c

@pytest.fixture()
def user_service() -> UserService:
    return UserService()

@pytest.fixture()
def role_service() -> RoleService:
    return RoleService()

@pytest.fixture()
def permission_service() -> PermissionService:
    return PermissionService()

# --- HR RBAC Test Utilities ---
HR_MANAGER_ROLE_NAME = "HR Manager (Test)"
HR_ASSISTANT_ROLE_NAME = "HR Assistant (Test)"
REGULAR_USER_ROLE_NAME = "Regular User (Test)"

HR_PERMISSIONS = {
    "department": ["department:create", "department:read", "department:update", "department:delete"],
    "designation": ["designation:create", "designation:read", "designation:update", "designation:delete"],
    "employee": ["employee:create", "employee:read", "employee:update", "employee:delete"],
}

@pytest_asyncio.fixture(scope="session")
async def hr_permissions_setup(permission_service: PermissionService): # Removed db_session, service can get it if needed or use its own
    # This fixture needs a session to interact with DB.
    # Since it's session-scoped, it needs its own session.
    async with TestAsyncSessionLocal() as session:
        all_perms_created = {}
        for entity_perms in HR_PERMISSIONS.values():
            for perm_name in entity_perms:
                existing_perm = await permission_service.get_permission_by_name(perm_name, session)
                if not existing_perm:
                    perm_in = PermissionCreate(name=perm_name, description=f"Permission for {perm_name}")
                    created = await permission_service.create_permission(perm_in, session)
                    all_perms_created[perm_name] = created
                else:
                    all_perms_created[perm_name] = existing_perm
        return all_perms_created


@pytest_asyncio.fixture(scope="session") # Made session-scoped for efficiency
async def hr_roles_setup(role_service: RoleService, hr_permissions_setup: dict[str, Permission]):
    async with TestAsyncSessionLocal() as session: # Needs its own session
        roles_created = {}

        hr_manager_perm_names = [p for sublist in HR_PERMISSIONS.values() for p in sublist]
        hr_manager_role = await role_service.get_role_by_name(HR_MANAGER_ROLE_NAME, session)
        if not hr_manager_role:
            hr_manager_role = await role_service.create_role(RoleCreate(name=HR_MANAGER_ROLE_NAME, description="Full HR Access (Test)"), session)
        for perm_name in hr_manager_perm_names:
            perm_obj = hr_permissions_setup.get(perm_name)
            if perm_obj:
                await role_service.assign_permission_to_role(hr_manager_role.id, perm_obj.id, session)
        roles_created[HR_MANAGER_ROLE_NAME] = hr_manager_role

        hr_assistant_perm_names = [
            HR_PERMISSIONS["department"][1], HR_PERMISSIONS["designation"][1],
            HR_PERMISSIONS["employee"][0], HR_PERMISSIONS["employee"][1],
        ]
        hr_assistant_role = await role_service.get_role_by_name(HR_ASSISTANT_ROLE_NAME, session)
        if not hr_assistant_role:
            hr_assistant_role = await role_service.create_role(RoleCreate(name=HR_ASSISTANT_ROLE_NAME, description="Limited HR Access (Test)"), session)
        for perm_name in hr_assistant_perm_names:
            perm_obj = hr_permissions_setup.get(perm_name)
            if perm_obj:
                await role_service.assign_permission_to_role(hr_assistant_role.id, perm_obj.id, session)
        roles_created[HR_ASSISTANT_ROLE_NAME] = hr_assistant_role

        regular_user_role = await role_service.get_role_by_name(REGULAR_USER_ROLE_NAME, session)
        if not regular_user_role:
            regular_user_role = await role_service.create_role(RoleCreate(name=REGULAR_USER_ROLE_NAME, description="Basic User Access (Test)"), session)
        roles_created[REGULAR_USER_ROLE_NAME] = regular_user_role

        return roles_created


@pytest_asyncio.fixture
async def test_hr_manager_user_with_token(
    user_service: UserService, hr_roles_setup: dict[str, Role]
) -> Tuple[User, str]:
    async with TestAsyncSessionLocal() as session: # Needs its own session for user creation
        username = f"test_hr_manager_{uuid.uuid4().hex[:6]}"
        email = f"{username}@example.com"
        user_in = UserCreate(username=username, email=email, password="password", is_active=True, is_email_verified=True)
        user = await user_service.create_user(user_in, session)
        hr_manager_role = hr_roles_setup[HR_MANAGER_ROLE_NAME]
        await user_service.assign_role_to_user(user.id, hr_manager_role.id, session)

        token = create_access_token(subject=str(user.id))
        # Must return user object that is not bound to the closed session, or re-fetch if needed by test
        return user, token # User object here is fine as long as tests don't try to lazy-load relationships on it later

@pytest_asyncio.fixture
async def test_hr_assistant_user_with_token(
    user_service: UserService, hr_roles_setup: dict[str, Role]
) -> Tuple[User, str]:
    async with TestAsyncSessionLocal() as session:
        username = f"test_hr_assistant_{uuid.uuid4().hex[:6]}"
        email = f"{username}@example.com"
        user_in = UserCreate(username=username, email=email, password="password", is_active=True, is_email_verified=True)
        user = await user_service.create_user(user_in, session)
        hr_assistant_role = hr_roles_setup[HR_ASSISTANT_ROLE_NAME]
        await user_service.assign_role_to_user(user.id, hr_assistant_role.id, session)

        token = create_access_token(subject=str(user.id))
        return user, token

@pytest_asyncio.fixture
async def test_regular_user_with_token(
    user_service: UserService, hr_roles_setup: dict[str, Role]
) -> Tuple[User, str]:
    async with TestAsyncSessionLocal() as session:
        username = f"test_regular_user_{uuid.uuid4().hex[:6]}"
        email = f"{username}@example.com"
        user_in = UserCreate(username=username, email=email, password="password", is_active=True, is_email_verified=True)
        user = await user_service.create_user(user_in, session)
        regular_role = hr_roles_setup[REGULAR_USER_ROLE_NAME]
        await user_service.assign_role_to_user(user.id, regular_role.id, session)

        token = create_access_token(subject=str(user.id))
        return user, token
