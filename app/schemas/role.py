import uuid
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from .permission import PermissionRead # Forward reference
else:
    from .permission import PermissionRead

class RoleBase(BaseModel): # Changed from SQLModel
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: uuid.UUID
    permissions: Optional[List['PermissionRead']] = [] # Add relationship, default to empty list

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel): # Changed from SQLModel
    name: Optional[str] = None
    description: Optional[str] = None
