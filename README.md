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
- **Testing Framework:** Pytest setup with `httpx` for async API testing and `pytest-asyncio`.
- **Configuration Management:** Settings managed via Pydantic and `.env` files.
- **uv Package Manager:** Project dependencies managed with `uv`.

## Project Structure

```
.
├── app/                    # Main application code
│   ├── core/               # Core components (config, security, dependencies, db session management)
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
├── .env.example            # Example environment file (TO BE CREATED by user)
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
    *   PostgreSQL database server

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
    *   Create a `.env` file in the project root. You can copy from `.env.example` if one is provided, or create it manually.
    *   **Required variables:**
        ```env
        DATABASE_URL="postgresql+asyncpg://your_db_user:your_db_password@your_db_host:your_db_port/your_db_name"
        SECRET_KEY="your_strong_random_secret_key_for_jwt"
        # Example: openssl rand -hex 32

        # Optional: For testing with a separate database
        # DATABASE_URL_TEST="postgresql+asyncpg://your_test_db_user:your_test_db_password@your_test_db_host:your_test_db_port/your_test_db_name"
        ```
    *   Replace placeholder values with your actual database credentials and a secure secret key.
    *   The `API_V1_STR` is set in `app/core/config.py` (default: `/api/v1`).

## Database Migrations (Alembic)

This project uses Alembic to manage database schema migrations.

1.  **Ensure your `DATABASE_URL` in the `.env` file is correctly configured and your database server is running.**

2.  **Apply Migrations:**
    To apply all pending migrations and bring the database schema up to date:
    ```bash
    uv run alembic upgrade head
    ```

3.  **Create New Migrations:**
    After making changes to your SQLModel definitions in `app/models/`, you need to generate a new migration script:
    ```bash
    uv run alembic revision -m "Your descriptive migration message" --autogenerate
    ```
    Review the generated script in `migrations/versions/` before applying it.

## Running the Application

1.  **Ensure your `.env` file is set up and migrations are applied.**

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

1.  **Ensure your test environment is configured.** If using a separate test database, make sure `DATABASE_URL_TEST` is set in your environment (e.g., in `pytest.ini` or system environment) and the test database exists.
    The current test setup in `tests/conftest.py` uses the main `DATABASE_URL` by default but is designed to be configurable.

2.  **Run Pytest:**
    ```bash
    uv run pytest
    ```
    This will discover and run all tests in the `tests/` directory.

## RBAC System Overview

The Role-Based Access Control system allows for fine-grained control over application resources.

*   **Users:** Represent individuals who can log in. Each user can be assigned one or more roles.
*   **Roles:** Collections of permissions. A role defines a set of capabilities (e.g., "Administrator", "HR Manager", "Read-Only User").
*   **Permissions:** Specific actions that can be performed (e.g., `users:create`, `employee_records:read`, `inventory:edit`). Permissions are assigned to roles.

**Workflow:**
1.  **Define Permissions:** Create `Permission` objects representing specific actions (e.g., via API or a seeding script).
2.  **Define Roles:** Create `Role` objects.
3.  **Assign Permissions to Roles:** Link `Permission`s to `Role`s.
4.  **Create Users:** Create `User` accounts.
5.  **Assign Roles to Users:** Link `User`s to `Role`s.
6.  **Protect Endpoints:** In your API routers, use dependencies (e.g., `Depends(get_current_active_superuser)` or a custom `Depends(require_permission("permission_name"))`) to check if the authenticated user has the necessary permissions via their roles.

## Key Environment Variables

Refer to the `.env` file setup section. The critical variables are:
- `DATABASE_URL`: Connection string for your main PostgreSQL database.
- `SECRET_KEY`: Secret key for JWT token generation and validation.
- `API_V1_STR` (defined in `app/core/config.py`): Base path for API V1, defaults to `/api/v1`.
- `DATABASE_URL_TEST` (optional, for tests): Connection string for a separate test database.
