from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

from app.models.mixin import UUIDMixin, TimestampAuditMixin

if TYPE_CHECKING:
    from .role import Role

from .associations import RolePermission

class Permission(SQLModel, UUIDMixin, TimestampAuditMixin, table=True):
    # UUIDMixin provides id field, so we remove it:
    # id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    # Relationships
    roles: List["Role"] = Relationship(back_populates="permissions", link_model=RolePermission)
    role_permissions: List["RolePermission"] = Relationship(back_populates="permission")