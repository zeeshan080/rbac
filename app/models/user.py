from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid
from datetime import datetime

from app.models.mixin import UUIDMixin, TimestampAuditMixin

if TYPE_CHECKING:
    from .role import Role
    from .associations import UserRole
    from .hr_models import Employee, LeaveRequest

from .associations import UserRole

class User(SQLModel, UUIDMixin, TimestampAuditMixin, table=True):
    # UUIDMixin provides id field, so we remove it
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True, index=True)
    full_name: str = Field(default="", nullable=False, max_length=255)
    profile_image: Optional[str] = Field(default=None, nullable=True, max_length=1000)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    # Fields for advanced user management
    is_email_verified: bool = Field(default=False, nullable=False)
    email_verification_token: Optional[str] = Field(default=None, index=True, unique=True, nullable=True, max_length=255)
    email_verification_token_expires_at: Optional[datetime] = Field(default=None, nullable=True)

    password_reset_token: Optional[str] = Field(default=None, index=True, unique=True, nullable=True, max_length=255)
    password_reset_token_expires_at: Optional[datetime] = Field(default=None, nullable=True)

    failed_login_attempts: int = Field(default=0, nullable=False)
    is_locked_out: bool = Field(default=False, nullable=False)
    lockout_until: Optional[datetime] = Field(default=None, nullable=True)

    hashed_password: str

    # Relationships
    employee_profile: Optional["Employee"] = Relationship(back_populates="user")
    reviewed_leave_requests: List["LeaveRequest"] = Relationship(back_populates="reviewed_by_user")
    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRole)
    user_roles: List["UserRole"] = Relationship(back_populates="user")