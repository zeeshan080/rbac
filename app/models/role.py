from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

if TYPE_CHECKING:
    from .permission import Permission
    from .user import User # Import User model for type checking

from .associations import UserRole # Keep these

from .associations import RolePermission # Keep these

class Role(SQLModel, table=True): # Role model itself
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    # This gives you the actual Permission objects assigned to the role:
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model=RolePermission
    )
    users: List["User"] = Relationship(
        back_populates="roles",
        link_model=UserRole
    )
    role_users: List["UserRole"] = Relationship(back_populates="role")  # Optional, for direct access to UserRole
    role_permissions: List["RolePermission"] = Relationship(
    back_populates="role"
    )
