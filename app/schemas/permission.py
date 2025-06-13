import uuid
from typing import Optional
from pydantic import BaseModel

class PermissionBase(BaseModel): # Changed from SQLModel
    name: str # e.g., "users:create", "posts:read"
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionRead(PermissionBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}

class PermissionUpdate(BaseModel): # Changed from SQLModel
    name: Optional[str] = None
    description: Optional[str] = None
