from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

if TYPE_CHECKING:
    from .role import Role

from .associations import RolePermission # Keep this


class Permission(SQLModel, table=True): # Permission model itself
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    roles: List["Role"] = Relationship(back_populates="permissions", link_model=RolePermission)
    role_permissions: List["RolePermission"] = Relationship(back_populates="permission")  # <-- Add this line
