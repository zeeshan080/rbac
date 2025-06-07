from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import async_engine # Import async_engine
from app.routers import login, users, roles, permissions
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: You could add initial checks or resource loading here if needed
    print(f"Application startup: {settings.PROJECT_NAME} - Engine pool ready.")
    yield
    # Shutdown: Dispose of the engine's connection pool
    print(f"Application shutdown: {settings.PROJECT_NAME} - Disposing of database engine pool...")
    await async_engine.dispose()
    print(f"Database engine pool for {settings.PROJECT_NAME} disposed.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Include RBAC routers using settings.API_V1_STR consistently
app.include_router(login.router, prefix=settings.API_V1_STR + "/login", tags=["login"])
app.include_router(users.router, prefix=settings.API_V1_STR + "/users", tags=["users"])
app.include_router(roles.router, prefix=settings.API_V1_STR + "/roles", tags=["roles"])
app.include_router(permissions.router, prefix=settings.API_V1_STR + "/permissions", tags=["permissions"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
