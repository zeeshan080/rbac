import uuid
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from .permission import PermissionRead # Forward reference

class RoleBase(BaseModel): # Changed from SQLModel
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: uuid.UUID
    permissions: Optional[List['PermissionRead']] = [] # Add relationship, default to empty list

    class Config:
        from_attributes = True

class RoleUpdate(BaseModel): # Changed from SQLModel
    name: Optional[str] = None
    description: Optional[str] = None
