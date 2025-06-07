import pytest
import pytest_asyncio # For async fixtures
from typing import AsyncGenerator, Generator

import httpx # For TestClient with async app
from fastapi import FastAPI
from sqlmodel.ext.asyncio.session import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
# Ensure SQLModel base is imported correctly if it's the one metadata is attached to
from sqlmodel import SQLModel # Assuming your models inherit from this SQLModel base

from app.main import app as main_app # The FastAPI application instance
from app.core.config import settings
from app.database import get_session # Original get_session
# app.models SQLModel is needed to create tables.
# The previous version had 'from app.models import SQLModel', which might be incorrect if SQLModel is imported directly from 'sqlmodel'
# and models are in app.models.*.
# The key is that SQLModel.metadata must contain all table definitions.
# This usually happens if all models are imported somewhere before SQLModel.metadata.create_all is called,
# AND they all inherit from a common base (like sqlmodel.SQLModel).

# Use a separate test database URL if available, otherwise use main DB (with caution)
TEST_DATABASE_URL = str(settings.DATABASE_URL)

# Create a new async engine for testing
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True) # echo=False for quieter tests

# Async session factory for tests
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """
    Fixture to create all tables in the test database before tests run.
    """
    # This requires all SQLModel table models to be imported so SQLModel.metadata knows about them.
    # This typically means ensuring app.models and all its contents are imported.
    # One way to ensure this is to import them here or in a central models.__init__.
    # For example:
    import app.models.user
    import app.models.role
    import app.models.permission
    import app.models.associations
    # Ensure the __init__.py in app.models also imports these if not already.

    async with test_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Use with caution
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Optional: Clean up tables after tests
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an async database session for a test.
    """
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture() # This fixture itself is not async, but it sets up an async override
def test_app(db_session: AsyncSession) -> Generator[FastAPI, None, None]:
    """
    Fixture to override the default 'get_session' dependency in the app
    with one that uses the test database session.
    """
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    main_app.dependency_overrides[get_session] = override_get_session
    yield main_app
    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(test_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Provides an async test client for making API requests.
    """
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as c:
        yield c
