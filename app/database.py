from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # Changed import
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel # Needed for SQLModel specific session features if any, or just for type hinting

from app.core.config import settings

# The database URL should be appropriate for asyncpg
# Example: "postgresql+asyncpg://user:password@host:port/dbname"
# Ensure your DATABASE_URL in .env is in this format if not already.
# The current Neon URL should work with asyncpg. Neon URLs are typically like:
# postgresql://user:password@project-id.region.neon.tech/dbname?sslmode=require
# asyncpg can often handle the "postgresql://" scheme directly.

from sqlalchemy.engine import make_url # Added for robust URL parsing

db_url_str = str(settings.DATABASE_URL)
url_object = make_url(db_url_str) # Parse the URL string
connect_args = {}

# Handle SSL for asyncpg if 'sslmode=require' is in the DSN
if url_object.query.get("sslmode") == "require":
    # Create a new query dictionary without 'sslmode'
    new_query = {k: v for k, v in url_object.query.items() if k != "sslmode"}
    # Reconstruct the URL object with the new query parameters
    url_object = url_object.set(query=new_query)
    connect_args["ssl"] = True # Use asyncpg's 'ssl' parameter

# Use the modified URL object (SQLAlchemy will convert it to string internally)
async_engine = create_async_engine(url_object, echo=True, future=True, connect_args=connect_args, pool_pre_ping=True)

# The AsyncSession for SQLModel should be configured like this:
# Note: Using SQLAlchemy's AsyncSession directly now.
# SQLModel's AsyncSession is a subclass, so this should be largely compatible.
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# SQLModel models are already declarative. No need for Base from sqlalchemy.ext.declarative.
# Alembic handles table creation, so create_db_and_tables (if it existed for sync) is not needed here.
