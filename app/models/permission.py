from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid # Import uuid

if TYPE_CHECKING:
    from .associations import RolePermission

class PermissionBase(SQLModel):
    name: str = Field(index=True, unique=True) # e.g., "users:create", "posts:read"
    description: Optional[str] = None

class Permission(PermissionBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True) # Use UUID

    roles: List["RolePermission"] = Relationship(back_populates="permission")

class PermissionCreate(PermissionBase):
    pass

class PermissionRead(PermissionBase):
    id: uuid.UUID # Use UUID

class PermissionUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
