from typing import Annotated, Optional
import uuid # For converting user_id string to UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError # JWTError is already imported in security.py, but good for clarity
from sqlmodel import Session, select # Using synchronous Session from SQLModel

from app.core.security import decode_token, TokenPayload
from app.models.user import User
from app.database import get_db # Using existing synchronous get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token") # Assuming API prefix

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_db)]
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

    user = session.get(User, user_id) # SQLModel synchronous session.get

    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
