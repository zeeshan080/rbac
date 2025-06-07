from typing import Annotated, Optional
import uuid # For converting user_id string to UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError # JWTError is already imported in security.py, but good for clarity
from sqlmodel.ext.asyncio.session import AsyncSession # Changed import
from sqlmodel import select # select is still needed

from app.core.security import decode_token, TokenPayload
from app.models.user import User
from app.database import get_session # Changed to get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token") # Assuming API prefix

async def get_current_user( # Made async
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)] # Changed Session to AsyncSession, get_db to get_session
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_payload = decode_token(token)
    if token_payload is None or token_payload.sub is None:
        raise credentials_exception

    try:
        # Assuming token_payload.sub is the user_id as a string representation of a UUID
        user_id = uuid.UUID(token_payload.sub)
    except ValueError:
        # If sub is not a valid UUID string
        raise credentials_exception

    user = await session.get(User, user_id) # SQLModel asynchronous session.get with await

    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user( # Made async
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_superuser( # Made async
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
