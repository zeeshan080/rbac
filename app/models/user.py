from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid

if TYPE_CHECKING:
    from .associations import UserRole # Keep this for the User model relationship
    # from app.schemas.role import RoleRead # No, models should not import schemas

class User(SQLModel, table=True): # User model itself
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    hashed_password: str

    roles: List["UserRole"] = Relationship(back_populates="user")
