from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
import uuid # Import uuid

if TYPE_CHECKING:
    from .associations import UserRole

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

class User(UserBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True) # Use UUID
    hashed_password: str

    roles: List["UserRole"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: uuid.UUID # Use UUID

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None
