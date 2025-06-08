import uuid
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, EmailStr # Ensure EmailStr is imported

if TYPE_CHECKING:
    from .role import RoleRead

class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: uuid.UUID
    is_email_verified: bool = False
    roles: Optional[List['RoleRead']] = []

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None

class UserReadMinimal(BaseModel): # For embedding in other schemas
    id: uuid.UUID
    username: str
    email: EmailStr # Added email as it's usually important for identification

    class Config:
        from_attributes = True
