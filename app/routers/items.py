from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import item as item_schema
from app.services import item_service
from app.database import get_db
# This import is needed to prevent circular import issues with User model
from app.schemas.user import User

router = APIRouter()

@router.post("/", response_model=item_schema.Item)
def create_item_for_user(
    user_id: int, item: item_schema.ItemCreate, db: Session = Depends(get_db)
):
    # Here you would typically get the current user from auth
    # For simplicity, we'll just use the user_id directly
    return item_service.create_user_item(db=db, item=item, user_id=user_id)

@router.get("/", response_model=list[item_schema.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = item_service.get_items(db, skip=skip, limit=limit)
    return items
