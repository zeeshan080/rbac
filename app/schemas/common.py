from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: Optional[int] = None
    size: Optional[int] = None
    # pages: Optional[int] = None # Derived: ceil(total / size)

    model_config = {"from_attributes": True} # For nested Pydantic models if T is also a Pydantic model from ORM
