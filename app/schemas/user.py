from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    items: list["Item"] = [] # Forward declaration for circular dependency

    class Config:
        orm_mode = True

from .item import Item # Import Item here to resolve forward declaration
