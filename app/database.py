from sqlmodel.ext.asyncio.session import AsyncSession, create_async_engine # Use SQLModel's async components
from sqlalchemy.orm import sessionmaker # Keep sessionmaker for AsyncSession configuration

from app.core.config import settings

# The database URL should be appropriate for asyncpg
# Example: "postgresql+asyncpg://user:password@host:port/dbname"
# Ensure your DATABASE_URL in .env is in this format if not already.
# The current Neon URL should work with asyncpg. Neon URLs are typically like:
# postgresql://user:password@project-id.region.neon.tech/dbname?sslmode=require
# asyncpg can often handle the "postgresql://" scheme directly.

async_engine = create_async_engine(str(settings.DATABASE_URL), echo=True, future=True)

# The AsyncSession for SQLModel should be configured like this:
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
) # Corrected: use 'bind=' for engine

async def get_session() -> AsyncSession: # Changed from get_db
    async with AsyncSessionLocal() as session:
        yield session

# SQLModel models are already declarative. No need for Base from sqlalchemy.ext.declarative.
# Alembic handles table creation, so create_db_and_tables (if it existed for sync) is not needed here.
