import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from app.main import app as main_app
from app.core.config import settings
from app.database import get_session
from app.services.user_service import UserService # Added import
# SQLModel import for metadata is not strictly needed here if Alembic handles everything
# and models are imported correctly when Alembic runs (e.g. in env.py or models package)

import os
from urllib.parse import urlparse # For ensuring asyncpg driver in test URL

# Determine Test Database URL
TEST_DATABASE_URL_STR = os.getenv("DATABASE_URL_TEST", settings.DATABASE_URL_TEST)
USING_MAIN_DB_FOR_TESTS = False

if not TEST_DATABASE_URL_STR:
    TEST_DATABASE_URL_STR = str(settings.DATABASE_URL)
    USING_MAIN_DB_FOR_TESTS = True
    print(f"WARNING: DATABASE_URL_TEST not set. Falling back to main DATABASE_URL for tests: {TEST_DATABASE_URL_STR}")
    print("This is NOT recommended for production testing. Please set a dedicated test database URL.")
else:
    # Ensure the test URL uses the asyncpg driver if it's postgresql
    if TEST_DATABASE_URL_STR.startswith("postgresql://"):
        TEST_DATABASE_URL_STR = TEST_DATABASE_URL_STR.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not TEST_DATABASE_URL_STR.startswith("postgresql+asyncpg://"):
        # Handle other cases or raise error if scheme is not postgresql based for asyncpg
        print(f"Warning: DATABASE_URL_TEST ('{TEST_DATABASE_URL_STR}') may not be correctly formatted for asyncpg.")
    print(f"Using dedicated test database: {TEST_DATABASE_URL_STR}")

# Create a new async engine for testing, configured with the test database URL
# Handle SSL for asyncpg if 'sslmode=require' is in the DSN for test DB
connect_args = {}
parsed_test_url = urlparse(TEST_DATABASE_URL_STR)
if 'sslmode=require' in parsed_test_url.query.lower():
    from urllib.parse import parse_qs, urlunparse, urlencode
    # Reconstruct URL without sslmode, as asyncpg takes ssl via connect_args
    query_params = parse_qs(parsed_test_url.query)
    new_query_params = {k: v[0] for k, v in query_params.items() if k.lower() != 'sslmode'}
    cleaned_query_string = urlencode(new_query_params)

    url_for_engine = urlunparse((
        parsed_test_url.scheme,
        parsed_test_url.netloc,
        parsed_test_url.path,
        parsed_test_url.params,
        cleaned_query_string,
        parsed_test_url.fragment
    ))
    connect_args["ssl"] = True
else:
    url_for_engine = TEST_DATABASE_URL_STR

test_engine = create_async_engine(url_for_engine, echo=False, connect_args=connect_args)

TestAsyncSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

def run_alembic_migrations_programmatically(database_url: str, alembic_ini_path: str = "alembic.ini"):
    """ Helper function to run Alembic migrations programmatically. """
    print(f"Running Alembic migrations on: {database_url if not USING_MAIN_DB_FOR_TESTS else 'MAIN DB (used as test DB)'}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    # Important: Override the script_location if your alembic.ini is not in the root
    # or if your test setup requires a different relative path.
    # For now, assuming alembic.ini is found correctly relative to where pytest is run.
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    print("Upgrading database to head...")
    alembic_command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied.")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    if USING_MAIN_DB_FOR_TESTS:
        print("WARNING: About to run migrations on MAIN database because DATABASE_URL_TEST was not set.")
        # Consider adding a stronger safeguard or prompt here if this is a common scenario.
        # For automated CI, this path should ideally lead to failure or use of ephemeral DBs.

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

@pytest.fixture() # Renamed test_app_with_overrides back to test_app for clarity
def test_app(db_session: AsyncSession) -> Generator[FastAPI, None, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    original_overrides = main_app.dependency_overrides.copy()
    main_app.dependency_overrides[get_session] = override_get_session
    yield main_app
    main_app.dependency_overrides = original_overrides

@pytest_asyncio.fixture()
async def client(test_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as c:
        yield c

@pytest.fixture()
def user_service() -> UserService: # Added fixture
    return UserService()
