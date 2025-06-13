from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, SQLModel, Relationship # Added Relationship
import uuid # Import uuid

if TYPE_CHECKING:
    from .user import User
    from .role import Role
    from .permission import Permission

class UserRole(SQLModel, table=True):
    user_id: uuid.UUID = Field(default=None, primary_key=True, foreign_key="user.id") # Use UUID
    role_id: uuid.UUID = Field(default=None, primary_key=True, foreign_key="role.id") # Use UUID

    user: Optional["User"] = Relationship(back_populates="user_roles")
    role: Optional["Role"] = Relationship(back_populates="role_users")


class RolePermission(SQLModel, table=True):
    role_id: uuid.UUID = Field(default=None, primary_key=True, foreign_key="role.id") # Use UUID
    permission_id: uuid.UUID = Field(default=None, primary_key=True, foreign_key="permission.id") # Use UUID

    role: Optional["Role"] = Relationship(back_populates="role_permissions")
    permission: Optional["Permission"] = Relationship(back_populates="role_permissions")
