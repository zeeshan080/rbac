import uuid
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, EmailStr # Use Pydantic's BaseModel for pure schemas

if TYPE_CHECKING:
    from .role import RoleRead # Forward reference for RoleRead

class UserBase(BaseModel): # Changed from SQLModel to Pydantic's BaseModel
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: uuid.UUID
    roles: Optional[List['RoleRead']] = [] # Add relationship, default to empty list

    class Config:
        from_attributes = True # Pydantic V1 style, or from_attributes = True for V2

class UserUpdate(BaseModel): # Changed from SQLModel
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None
