import uuid
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, EmailStr # Ensure EmailStr is imported

from pydantic import BaseModel, EmailStr
from typing import List
import uuid

if TYPE_CHECKING:
    from .role import RoleRead
else:
    # Import RoleRead at runtime for model_rebuild
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

    model_config = {"from_attributes": True}

UserRead.model_rebuild()

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

    model_config = {"from_attributes": True}


class UserCreateWithRoles(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_active: bool = True
    is_superuser: bool = False
    role_ids: List[uuid.UUID]