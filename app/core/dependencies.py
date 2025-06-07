from typing import Annotated, Optional, Callable, Awaitable # Added Callable, Awaitable
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
# jose.JWTError is not directly used here but was in original, keep if no harm.
# from jose import JWTError

from sqlmodel.ext.asyncio.session import AsyncSession
# select might not be used directly here but was in original
# from sqlmodel import select

from app.core.security import decode_token, TokenPayload
from app.models.user import User
from app.database import get_session # Corrected from app.database import get_db
from app.services.user_service import UserService # Added for require_permission
from app.core.logging_config import get_logger # Added for logging

logger = get_logger(__name__) # Added

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token") # Path from settings.API_V1_STR

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_payload = decode_token(token)
    if token_payload is None or token_payload.sub is None:
        logger.warning("Token decoding failed or subject (user ID) missing from token.")
        raise credentials_exception

    try:
        user_id = uuid.UUID(token_payload.sub)
    except ValueError:
        logger.warning(f"Invalid user ID format in token subject: {token_payload.sub}")
        raise credentials_exception

    user = await session.get(User, user_id) # Efficiently fetch user by ID
    if user is None:
        logger.warning(f"User not found for ID: {user_id} from token.")
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        logger.warning(f"Authentication attempt by inactive user: {current_user.username} (ID: {current_user.id})")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not current_user.is_superuser:
        logger.warning(f"Privileged access denied for non-superuser: {current_user.username} (ID: {current_user.id})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (superuser required)."
        )
    return current_user

# Type alias for the dependency function returned by the factory
# Using Awaitable[User] as the callable should return an awaitable that resolves to User
PermissionDependency = Callable[[User, AsyncSession, UserService], Awaitable[User]]

def require_permission(required_permission_name: str) -> Callable[..., Awaitable[User]]: # Simpler return type hint for Depends
    """
    Dependency factory that creates a dependency to check for a specific permission.
    Usage: Depends(require_permission("some:permission"))
    """
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
        user_service: Annotated[UserService, Depends(UserService)] # Inject UserService
    ) -> User: # The dependency itself returns the User if successful
        logger.debug(f"Permission check: User '{current_user.username}' requires '{required_permission_name}'.")

        # Superusers bypass permission checks
        if current_user.is_superuser:
            logger.debug(f"User '{current_user.username}' is superuser. Access granted for '{required_permission_name}'.")
            return current_user

        user_permissions = await user_service.get_user_permission_names(user=current_user, session=session)

        if required_permission_name not in user_permissions:
            logger.warning(
                f"Permission Denied: User '{current_user.username}' lacks required permission '{required_permission_name}'. "
                f"User has permissions: {user_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Requires: '{required_permission_name}'.",
            )

        logger.debug(f"Permission Granted: User '{current_user.username}' has required permission '{required_permission_name}'.")
        return current_user

    return permission_checker
