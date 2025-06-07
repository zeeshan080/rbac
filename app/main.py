from fastapi import FastAPI
from app.routers import items, users
from app.core.config import settings
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])

@app.get("/")
async def root():
    return {"message": "Hello World"}
