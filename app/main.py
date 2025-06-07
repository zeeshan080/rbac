from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status # Request was added for exception handlers
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import async_engine
# Updated imports for routers
from app.routers import login, users, roles, permissions, department_router, designation_router, employee_router # Added employee_router
from app.core.config import settings
from app.core.logging_config import get_logger
import app.core.logging_config # Initialize logging

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Application startup: {settings.PROJECT_NAME} - Engine pool ready.")
    yield
    logger.info(f"Application shutdown: {settings.PROJECT_NAME} - Disposing of database engine pool...")
    await async_engine.dispose()
    logger.info(f"Database engine pool for {settings.PROJECT_NAME} disposed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
    # TODO: Add OpenAPI documentation metadata (version, description, contact, license_info)
    # version="0.1.0",
    # description="FastAPI RBAC Application with HR module.",
    # contact={"name": "Admin", "email": "admin@example.com"},
)

# Custom Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        logger.error(f"HTTPException for {request.method} {request.url.path}: {exc.status_code} {exc.detail}", exc_info=True) # exc_info=True for 500s
    else:
        logger.warning(f"HTTPException for {request.method} {request.url.path}: {exc.status_code} {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.warning(f"Request validation error for {request.method} {request.url.path}: {error_details}")
    from fastapi.exception_handlers import request_validation_exception_handler
    return await request_validation_exception_handler(request, exc)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled exception for {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "An unexpected internal server error occurred. Please contact support."})

# Include existing RBAC and auth routers
app.include_router(login.router, prefix=settings.API_V1_STR + "/login", tags=["Login"])
app.include_router(users.router, prefix=settings.API_V1_STR + "/users", tags=["Users"])
app.include_router(roles.router, prefix=settings.API_V1_STR + "/roles", tags=["Roles"])
app.include_router(permissions.router, prefix=settings.API_V1_STR + "/permissions", tags=["Permissions"])

# Include new HR routers
HR_API_PREFIX = settings.API_V1_STR + "/hr"
app.include_router(department_router.router, prefix=HR_API_PREFIX + "/departments", tags=["HR - Departments"])
app.include_router(designation_router.router, prefix=HR_API_PREFIX + "/designations", tags=["HR - Designations"])
app.include_router(employee_router.router, prefix=HR_API_PREFIX + "/employees", tags=["HR - Employees"]) # Added employee_router

@app.get("/")
async def root(request: Request): # Added Request for logging client
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Root path '/' accessed by client: {client_host}.")
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
