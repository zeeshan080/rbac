from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid
from datetime import datetime # Ensure datetime is imported

if TYPE_CHECKING:
    from .associations import UserRole
    from .hr_models import Employee # Added import for Employee

class User(SQLModel, table=True): # User model itself
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True, index=True)
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

    roles: List["UserRole"] = Relationship(back_populates="user")

    # Link to HR Employee profile if this user is an employee
    employee_profile: Optional["Employee"] = Relationship(back_populates="user")
