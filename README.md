# FastAPI RBAC Application

A robust FastAPI application featuring a Role-Based Access Control (RBAC) system, JWT authentication, asynchronous database operations with SQLModel and Alembic for migrations.

## Features

- **Role-Based Access Control (RBAC):** Manage Users, Roles, and Permissions. Assign multiple roles to users and multiple permissions to roles.
- **JWT Authentication:** Secure API endpoints using JSON Web Tokens.
- **Asynchronous Operations:** Fully async application stack using FastAPI and SQLModel's async support with `asyncpg`.
- **SQLModel ORM:** Pythonic object-relational mapping with Pydantic validation.
- **Alembic Migrations:** Handle database schema changes systematically.
- **Pydantic Schemas:** Clear data validation and serialization for API requests and responses.
- **Dependency Injection:** FastAPI's dependency injection for services, database sessions, and authentication.
- **Testing Framework:** Pytest setup with `httpx` for async API testing and `pytest-asyncio`. Supports dedicated test database.
- **Configuration Management:** Settings managed via Pydantic and `.env` files.
- **uv Package Manager:** Project dependencies managed with `uv`.
- **Data Seeding:** CLI command to populate initial permissions, roles, and a superuser.
- **Advanced User Features:** Email verification, password reset, account lockout.

## Project Structure

```
.
├── app/                    # Main application code
│   ├── cli.py              # Typer CLI application (e.g., for seeding)
│   ├── core/               # Core components (config, security, dependencies, logging, initial_data_config)
│   ├── db/                 # Database related utilities (e.g., seed.py)
│   ├── models/             # SQLModel database models & association tables
│   ├── routers/            # API endpoint definitions (FastAPI routers)
│   ├── schemas/            # Pydantic schemas for request/response validation
│   └── services/           # Business logic layer
│   └── main.py             # FastAPI application instance and startup
├── migrations/             # Alembic migration scripts
│   └── versions/
│   └── env.py              # Alembic environment configuration
│   └── script.py.mako      # Alembic script template
├── tests/                  # Test suite
│   ├── api/                # API endpoint tests
│   ├── unit/               # Unit tests
│   └── conftest.py         # Pytest shared fixtures
├── .env.example            # Example environment file
├── .env                    # Actual environment variables (gitignored)
├── alembic.ini             # Alembic configuration file
├── pytest.ini              # Pytest configuration file
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.8+
    *   `uv` package manager (Install with `pip install uv`)
    *   PostgreSQL database server (ensure it's running and accessible)

2.  **Clone the Repository:**
    ```bash
    # git clone <repository-url>
    # cd <repository-name>
    ```
    (Assuming you have the code locally for now)

3.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install Dependencies:**
    Use `uv` to install dependencies from `requirements.txt`:
    ```bash
    uv pip install -r requirements.txt
    ```

5.  **Set Up Environment Variables:**
    *   Create a `.env` file in the project root by copying from `.env.example`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and provide actual values for:
        *   `DATABASE_URL`: Your main PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@host:port/dbname`).
        *   `SECRET_KEY`: A strong, random string for JWT security (e.g., generate with `openssl rand -hex 32`).
        *   `DEFAULT_SUPERUSER_PASSWORD`: The password for the initial superuser that will be created by the data seeder. **Choose a strong password.**
        *   (Optional) `DATABASE_URL_TEST`: Connection string for a separate test database if you intend to run tests that require one.
        *   (Optional) `LOG_LEVEL`: Set the application log level (e.g., INFO, DEBUG).
    *   The `API_V1_STR` is set in `app/core/config.py` (default: `/api/v1`). Other settings like token expiry and lockout policy are also in `config.py` with defaults, and can be overridden via `.env`.

## Database Migrations (Alembic)

This project uses Alembic to manage database schema changes.

1.  **Ensure your `DATABASE_URL` in the `.env` file is correctly configured and your database server is running.**

2.  **Apply Migrations:**
    To apply all pending migrations and bring the database schema up to date (or create it if it's the first time):
    ```bash
    uv run alembic upgrade head
    ```
    *If setting up for the first time, it's generally recommended to run migrations **before** seeding initial data.*

## Initial Data Seeding

After setting up your `.env` file (especially `DATABASE_URL` and `DEFAULT_SUPERUSER_PASSWORD`) and ensuring the database schema is migrated to the latest version (`uv run alembic upgrade head`), you can populate the database with initial data. This includes:
- Default permissions for system administration and HR module functionalities.
- Default roles ("System Administrator", "HR Manager", "HR Assistant", "Basic User") with appropriate permissions assigned.
- A default superuser account (email and username configured in `app/core/initial_data_config.py`, password from `DEFAULT_SUPERUSER_PASSWORD` in `.env`).

**To run the seeder:**
```bash
# Ensure your virtual environment is active and .env file is configured.
# Make sure PYTHONPATH is set to include your project root for the app module to be found.
# If in project root:
export PYTHONPATH=.
python app/cli.py seed-data
# Or using uv (which might handle PYTHONPATH if configured in pyproject.toml, but explicit export is safer for scripts):
# uv run python app/cli.py seed-data
```
This command should typically be run once for a new database setup. The script is designed to be idempotent (safe to run multiple times, though it will log if items already exist).

## Running the Application

1.  **Ensure your `.env` file is set up, migrations are applied, and initial data is seeded.**

2.  **Start the Uvicorn Server:**
    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    *   `--reload`: Enables auto-reloading when code changes (for development).
    *   `--host 0.0.0.0`: Makes the server accessible from your network.
    *   `--port 8000`: Runs on port 8000.

3.  **Access API Documentation:**
    Once the server is running, you can access the interactive API documentation (Swagger UI) at:
    [http://localhost:8000/docs](http://localhost:8000/docs)

    And ReDoc documentation at:
    [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Running Tests

1.  **Configure Test Database:**
    *   Ensure you have a separate PostgreSQL database dedicated for testing.
    *   Set the `DATABASE_URL_TEST` environment variable in your `.env` file (or `pytest.ini`) to point to this test database.
    *   Example in `.env`: `DATABASE_URL_TEST="postgresql+asyncpg://test_user:test_pass@localhost/test_db_name"`
    *   The test setup (`tests/conftest.py`) will automatically run Alembic migrations to prepare this test database schema.

2.  **Run Pytest:**
    ```bash
    uv run pytest
    ```
    This will discover and run all tests in the `tests/` directory.

## RBAC System Overview

The Role-Based Access Control system allows for fine-grained control over application resources.

*   **Permissions:** Specific actions that can be performed (e.g., `users:create`, `employee:read`). Defined in `app/core/initial_data_config.py` and created by the seeder.
*   **Roles:** Collections of permissions (e.g., "Administrator", "HR Manager"). Defined in `app/core/initial_data_config.py` and created by the seeder, with permissions assigned.
*   **Users:** Represent individuals. Each user is assigned one or more roles. A default superuser is created by the seeder.

**Workflow for Access Control:**
1.  Permissions, Roles, and Role-Permission links are created by the `seed-data` CLI command.
2.  Users are created (e.g., default superuser by seeder, others via API) and assigned roles.
3.  API Endpoints are protected by the `Depends(require_permission("permission_name"))` dependency, which checks if the authenticated user has the necessary permission via their roles. Superusers bypass these specific permission checks.

## Key Environment Variables

(Refer to your `.env` file, based on `.env.example`)
- `DATABASE_URL`: Connection string for your main PostgreSQL database.
- `SECRET_KEY`: Secret key for JWT token generation and validation.
- `DEFAULT_SUPERUSER_PASSWORD`: Password for the initial superuser created by the seeder.
- `API_V1_STR` (defined in `app/core/config.py`): Base path for API V1, defaults to `/api/v1`.
- `DATABASE_URL_TEST` (optional but highly recommended for tests): Connection string for a separate test database.
- `LOG_LEVEL`: (e.g., INFO, DEBUG) Controls application logging verbosity.
- `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS`: Duration for email verification token validity.
- `PASSWORD_RESET_TOKEN_EXPIRE_HOURS`: Duration for password reset token validity.
- `MAX_FAILED_LOGIN_ATTEMPTS`: Number of failed login attempts before account lockout.
- `ACCOUNT_LOCKOUT_DURATION_MINUTES`: Duration for account lockout.
