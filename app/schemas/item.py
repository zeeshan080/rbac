from pydantic import BaseModel

class ItemBase(BaseModel):
    title: str
    description: str | None = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

# Add Item schema to User schema to avoid circular imports
from .user import UserBase

class UserWithItems(UserBase):
    items: list[Item] = []

    class Config:
        orm_mode = True
