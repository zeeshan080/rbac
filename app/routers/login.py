from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import create_access_token, verify_password
from app.core.dependencies import get_current_active_user
from app.services.user_service import UserService
from app.schemas.token import Token # Using the new app.schemas.token.Token
from app.schemas.user import UserRead # Import UserRead
from app.database import get_session
from app.models.user import User # For type hint

router = APIRouter()

# Token schema is now in app/schemas/token.py

@router.post("/access-token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_service: Annotated[UserService, Depends(UserService)] # Use FastAPI's dependency injection
):
    user = await user_service.get_user_by_username(username=form_data.username, session=session)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")

@router.get("/test-token", response_model=UserRead)
async def test_token(current_user: Annotated[User, Depends(get_current_active_user)]):
    # get_current_active_user returns a User model instance.
    # UserRead.from_attributes will convert it.
    return UserRead.from_attributes(current_user)
