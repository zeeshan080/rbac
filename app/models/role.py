from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

from app.models.mixin import UUIDMixin, TimestampAuditMixin

if TYPE_CHECKING:
    from .permission import Permission
    from .user import User

from .associations import UserRole, RolePermission

class Role(SQLModel, UUIDMixin, TimestampAuditMixin, table=True):
    # UUIDMixin provides id field, so we remove it:
    # id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    # Relationships
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model=RolePermission
    )
    users: List["User"] = Relationship(
        back_populates="roles",
        link_model=UserRole
    )
    role_users: List["UserRole"] = Relationship(back_populates="role")
    role_permissions: List["RolePermission"] = Relationship(back_populates="role")