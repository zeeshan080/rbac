from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status # Added Request for handler signatures
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import async_engine
from app.routers import login, users, roles, permissions
from app.core.config import settings
from app.core.logging_config import get_logger # Import get_logger

# Initialize logging_config by importing it (basicConfig runs)
import app.core.logging_config # This line ensures basicConfig is called

logger = get_logger(__name__) # Logger for main.py (e.g., app.main)

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
)

# --- Custom Exception Handlers ---
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Log with more severity for server errors
    if exc.status_code >= 500:
        logger.error(f"HTTPException {exc.status_code} for {request.method} {request.url.path}: {exc.detail}", exc_info=exc if exc.status_code >=500 else None)
    else:
        logger.warning(f"HTTPException {exc.status_code} for {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the detailed validation errors
    error_details = exc.errors()
    logger.warning(f"Request validation error for {request.method} {request.url.path}: {error_details}")
    # Re-use FastAPI's default handler logic for the response structure for consistency
    from fastapi.exception_handlers import request_validation_exception_handler
    return await request_validation_exception_handler(request, exc)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled exception for {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred. Please contact support."},
    )

# Include RBAC routers
app.include_router(login.router, prefix=settings.API_V1_STR + "/login", tags=["login"])
app.include_router(users.router, prefix=settings.API_V1_STR + "/users", tags=["users"])
app.include_router(roles.router, prefix=settings.API_V1_STR + "/roles", tags=["roles"])
app.include_router(permissions.router, prefix=settings.API_V1_STR + "/permissions", tags=["permissions"])

@app.get("/")
async def root(request: Request): # Added Request for potential client info logging
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Root path '/' accessed by client: {client_host}.")
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
