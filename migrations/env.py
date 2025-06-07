import asyncio
import os # Added os for path manipulation, though not used in final version of this script
import sys # Added sys for path manipulation, though not used in final version of this script
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # This path append is no longer in the provided script, assuming direct imports work or PYTHONPATH is set

from logging.config import fileConfig
from urllib.parse import urlparse, parse_qs, urlunparse # Added urlunparse

from sqlalchemy.ext.asyncio import create_async_engine # Direct import
from alembic import context
from sqlmodel import SQLModel # For target_metadata

# Import your models here so Alembic can see them for autogenerate
# Make sure app.models eventually imports all your models
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import UserRole, RolePermission
# If you have a base model or a central __init__ in app.models that imports all, use that:
# from app.models import *

from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# Common migration function for online mode (used by run_sync)
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True, # Recommended for SQLModel/SQLAlchemy
        render_as_batch=True # Good practice, esp. for SQLite
    )
    with context.begin_transaction():
        context.run_migrations()

# Async online migration function
async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    db_url_str = str(settings.DATABASE_URL)
    connect_args = {}

    # Ensure the URL scheme is compatible with asyncpg
    # and handle SSL configuration for asyncpg
    parsed_url = urlparse(db_url_str)
    scheme = parsed_url.scheme

    if scheme == "postgresql":
        scheme = "postgresql+asyncpg" # Ensure asyncpg driver is specified

    current_query_params = parse_qs(parsed_url.query)
    new_query_params = {}

    for key, value in current_query_params.items():
        if key.lower() == 'sslmode':
            if value[0] == 'require':
                connect_args["ssl"] = True # For asyncpg
            # Other sslmode values could be mapped to asyncpg's ssl.SSLContext if needed
            # For 'allow', 'prefer', 'verify-ca', 'verify-full', asyncpg might need specific SSLContext
            # For now, only 'require' is explicitly translated.
        else:
            new_query_params[key] = value[0] # parse_qs returns list for values

    # Reconstruct URL without sslmode, as asyncpg takes ssl via connect_args
    # Using urlunparse requires a tuple: (scheme, netloc, path, params, query, fragment)
    # For query, it should be a string like 'key=value&key2=value2'
    from urllib.parse import urlencode
    cleaned_query_string = urlencode(new_query_params)

    final_url_str = urlunparse((
        scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        cleaned_query_string,
        parsed_url.fragment
    ))

    connectable = create_async_engine(
        final_url_str,
        connect_args=connect_args,
        # echo=True, # Optional: for debugging SQL
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

# Offline migration function (remains synchronous)
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    # For offline mode, we generally don't need to process sslmode for asyncpg,
    # as it's about generating SQL, not connecting.
    # However, if the URL itself causes issues for SQLAlchemy's offline dialect,
    # minimal cleaning might be needed. The original DATABASE_URL should be fine.
    url = str(settings.DATABASE_URL)
    context.configure(
        url=url, # Use original or minimally cleaned URL
        target_metadata=target_metadata,
        literal_binds=True, # Recommended for script generation
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

# Determine mode and run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Ensure PYTHONPATH includes the project root if 'app' is not found
    # This can be set before running alembic, or sys.path can be manipulated here.
    # The provided script for this turn does not include the sys.path.append line anymore here.
    # It relies on PYTHONPATH being set externally (e.g., by `export PYTHONPATH=.`)
    asyncio.run(run_migrations_online())
