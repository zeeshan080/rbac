from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

if TYPE_CHECKING:
    from .associations import UserRole, RolePermission # Keep these

class Role(SQLModel, table=True): # Role model itself
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    users: List["UserRole"] = Relationship(back_populates="role")
    permissions: List["RolePermission"] = Relationship(back_populates="role")
