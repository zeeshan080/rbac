import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from pydantic import EmailStr, BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserCreateWithRoles
from app.schemas.common import Page
from app.schemas.auth import PasswordResetRequestSchema, NewPasswordSchema
from app.models.user import User
from enum import Enum

from app.core.dependencies import get_current_active_user, get_current_active_superuser

from enum import Enum
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from pydantic import EmailStr
from app.core.logging_config import get_logger
# --- Reusable query parameters ---
logger = get_logger(__name__)

# Restrictable fields for ordering
class UserOrderBy(str, Enum):
    id = "id"
    username = "username"
    email = "email"
    created_at = "created_at"
    updated_at = "updated_at"

class UserFilterField(str, Enum):
    username = "username"
    email = "email"
    is_active = "is_active"
    is_superuser = "is_superuser"
    is_email_verified = "is_email_verified"


class UserSearchField(str, Enum):
    username = "username"
    email = "email"
    full_name = "full_name"  
  

# Simple dependency function
def get_user_service() -> UserService:
    return UserService()

router = APIRouter()
#service = UserService()  # Create instance directly


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Optional[User] = Depends(get_current_active_user),
):
    """Create a new user."""
    # Check for existing username/email
    existing_user = await service.get_user_by_username(user_in.username, session)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    
    existing_email = await service.get_user_by_email(user_in.email, session)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    
    user = await service.create(user_in, session, current_user.id if current_user else None)
    
    # Optionally trigger email verification
    # try:
    #     await service.request_email_verification(user.email, session)
    # except Exception as e:
    #     # Log but don't break user creation if email verification fails
    #     pass  # In production, you should log this error
        
    return UserRead.model_validate(user)

@router.post("/with-roles", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_with_roles(
    user_in: UserCreateWithRoles,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    """Create a new user with assigned roles (superuser only)."""
    # Check for existing username/email
    existing_user = await service.get_user_by_username(user_in.username, session)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    
    existing_email = await service.get_user_by_email(user_in.email, session)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    
    # Create user with roles - this method already uses create internally
    user = await service.create_user_with_roles(
        user_in=UserCreate(
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
            full_name=user_in.full_name if hasattr(user_in, "full_name") else "",
        ),
        role_ids=user_in.role_ids,
        session=session,
        user_id=current_user.id,  # Use current_user for audit
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create user with roles"
        )
        
    return UserRead.model_validate(user)

@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Get information about the currently authenticated user."""
    # We need to reload the user to ensure roles are populated
    user = await service.get(current_user.id, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


# ...existing imports...

@router.get("/", response_model=Page[UserRead])
async def get_users(
    # Dependencies
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    service: Annotated[UserService, Depends(get_user_service)],

    # Pagination
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),

    # Ordering
    order_by: UserOrderBy = Query(UserOrderBy.created_at),
    order_desc: bool = Query(True),

    # Filter & Search models
    filter_params: UserFilterField = Query(None, description="Fields to filter by"),
    search_params: UserSearchField = Query(None,description="Fields to search by"),
    search_term: Optional[str] = Query(None, description="Search term for partial matches"),
):
    """
    Combined endpoint to:
    1. List all users (no filters, no search).
    2. Filter users by exact matches if filter values are provided.
    3. Search users by partial matches if `search_params.search` is provided.

    Returns a paginated list of users.
    """
    logger.info(f"Fetching users with filters: {filter_params}, search: {search_params}, term: {search_term}")
    # Combine filtering & searching in a single call
    result = await service.filter_and_search(
        session=session,
        skip=skip,
        limit=limit,
        order_by=order_by.value,
        order_desc=order_desc,
        # <--- pass the search term
        search_term=search_term if search_term else "",  # <--- pass the search term
        search_field=search_params.value if search_params else "",    # <--- pass the search fields
        filter_param=filter_params.value if filter_params else "",  # <--- pass the filter params
    )

    return result

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: uuid.UUID = Path(..., description="The UUID of the user to fetch"),
):
    """Get user details by ID."""
    # Non-superusers can only view themselves
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    user = await service.get(user_id, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserRead.model_validate(user)

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: uuid.UUID = Path(..., description="The UUID of the user to update"),
    user_in: UserUpdate = Body(..., description="User data to update"),
):
    """Update user information."""
    # Check permissions
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions to update this user"
        )

    # Get target user to validate against
    target_user = await service.get(user_id, session)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User to update not found"
        )

    # Additional validation for non-superusers
    if not current_user.is_superuser:
        if user_in.is_superuser is True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Cannot make user a superuser"
            )
            
        if user_in.is_active is not None and user_in.is_active != target_user.is_active:
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN, 
                 detail="Cannot change active status"
             )
             
        if user_in.email is not None and user_in.email != target_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Non-superusers cannot change email addresses directly. Please contact support."
            )

    # Update user with improved update method that handles password hashing
    user_dict = user_in.model_dump(exclude_unset=True)
    updated_user = await service.update(
        id=user_id, 
        obj_in=user_dict, 
        session=session,
        user_id=current_user.id,  # For audit trail
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update user"
        )

    # Handle email verification if email was changed by a superuser
    old_email = target_user.email
    new_email = updated_user.email
    
    if (user_in.email is not None and 
        old_email != new_email and 
        current_user.is_superuser):
        
        # Reset verification status for changed email
        updated_user.is_email_verified = False
        updated_user.email_verification_token = None
        updated_user.email_verification_token_expires_at = None
        
        session.add(updated_user)
        await session.commit()
        
        # Send verification email
        await service.request_email_verification(updated_user.email, session)
        await session.refresh(updated_user)

    return UserRead.model_validate(updated_user)

@router.delete("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def delete_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    user_id: uuid.UUID = Path(..., description="The UUID of the user to delete"),
    permanent: bool = Query(default=False, description="Whether to permanently delete or soft-delete"),
):
    """Delete a user (superuser only)."""
    # Prevent deleting yourself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot delete yourself"
        )
    
    # Check if user exists
    target_user = await service.get(user_id, session)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    # Choose between soft delete and permanent delete
    if permanent:
        deleted_user = await service.delete(user_id, session, current_user.id)
    else:
        deleted_user = await service.soft_delete(user_id, session, current_user.id)
    
    if not deleted_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to delete user"
        )
        
    return UserRead.model_validate(deleted_user)

@router.post("/{user_id}/restore", response_model=UserRead)
async def restore_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    user_id: uuid.UUID = Path(..., description="The UUID of the user to restore"),
):
    """Restore a soft-deleted user (superuser only)."""
    restored_user = await service.restore(user_id, session, current_user.id)
    
    if not restored_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found or not soft-deleted"
        )
        
    return UserRead.model_validate(restored_user)

@router.post("/{user_id}/roles/{role_id}", response_model=UserRead)
async def assign_role_to_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    user_id: uuid.UUID = Path(..., description="The user ID"),
    role_id: uuid.UUID = Path(..., description="The role ID to assign"),
):
    """Assign a role to a user (superuser only)."""
    user = await service.assign_role_to_user(user_id=user_id, role_id=role_id, session=session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User or Role not found"
        )
        
    return UserRead.model_validate(user)

@router.delete("/{user_id}/roles/{role_id}", response_model=UserRead)
async def revoke_role_from_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    user_id: uuid.UUID = Path(..., description="The user ID"),
    role_id: uuid.UUID = Path(..., description="The role ID to revoke"),
):
    """Revoke a role from a user (superuser only)."""
    user = await service.revoke_role_from_user(user_id=user_id, role_id=role_id, session=session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found or role not assigned"
        )
        
    return UserRead.model_validate(user)

# --- Email Verification Endpoints ---

class EmailVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/request-verification-email", status_code=status.HTTP_202_ACCEPTED)
async def request_verification_email(
    request_data: EmailVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Request a new email verification link."""
    # Always return 202 regardless of result to prevent user enumeration
    await service.request_email_verification(email=request_data.email, session=session)
    return {
        "message": "If an account with this email exists and is not yet verified, a verification email has been sent."
    }

@router.get("/verify-email/{token}", response_model=UserRead)
async def verify_email(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    token: str = Path(..., description="The verification token"),
):
    """Verify user email with token."""
    user = await service.verify_email(token=token, session=session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used verification token."
        )
        
    return UserRead.model_validate(user)

# --- Password Reset Endpoints ---

@router.post("/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    request_data: PasswordResetRequestSchema,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Request a password reset link."""
    # Always return 202 regardless of result to prevent user enumeration
    await service.request_password_reset(email=request_data.email, session=session)
    return {
        "message": "If an account with this email exists, a password reset link has been sent."
    }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: NewPasswordSchema,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Reset password using a token."""
    success = await service.reset_password_with_token(
        token=request_data.token,
        new_password=request_data.new_password,
        session=session
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used password reset token."
        )
        
    return {"message": "Password has been reset successfully."}