from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid # Import uuid

if TYPE_CHECKING:
    from .associations import UserRole, RolePermission

class RoleBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class Role(RoleBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True) # Use UUID

    users: List["UserRole"] = Relationship(back_populates="role")
    permissions: List["RolePermission"] = Relationship(back_populates="role")

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: uuid.UUID # Use UUID

class RoleUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
