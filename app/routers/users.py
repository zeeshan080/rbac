import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import EmailStr, BaseModel # EmailStr, BaseModel are used by EmailVerificationRequest

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserCreateWithRoles
from app.schemas.common import Page
from app.schemas.auth import PasswordResetRequestSchema, NewPasswordSchema # Added for password reset
from app.models.user import User # For current_user type hint
from app.core.dependencies import get_current_active_user, get_current_active_superuser

router = APIRouter()
service_dependency = Depends(UserService)

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    existing_user = await service.get_user_by_username(user_in.username, session)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    existing_email = await service.get_user_by_email(user_in.email, session)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = await service.create_user(user_in=user_in, session=session)
    # Consider auto-triggering email verification:
    # This is a good place to do it if users should verify upon creation.
    # Ensure the service method handles cases where email sending might fail without breaking user creation.
    # For example:
    # try:
    #     await service.request_email_verification(user.email, session)
    # except Exception as e: # Catch broad exceptions if email sending is non-critical for user creation
    #     logger.error(f"Failed to send verification email for user {user.username} during creation: {e}")
    return UserRead.model_validate(user)

@router.post("/with-roles", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_with_roles_endpoint(
    user_in: UserCreateWithRoles,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    existing_user = await service.get_user_by_username(user_in.username, session)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    existing_email = await service.get_user_by_email(user_in.email, session)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Use the function you created
    user = await service.create_user_with_roles(
        user_in=UserCreate(
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
        ),
        role_ids=user_in.role_ids,
        session=session,
    )
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, Depends(UserService)],
):
    user_with_roles = await service.get_user_with_roles(current_user.id, session)
    return UserRead.model_validate(user_with_roles)


@router.get("/", response_model=Page[UserRead])
async def read_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    order_by: str = Query(default="id", description="Field to order by, e.g., 'username', 'email', 'created_at'"),
    order_desc: bool = Query(default=False, description="Order direction, true for descending, false for ascending"),
    search: str = Query(default=None, description="Search term for username or email"),
):
    return await service.get_users(skip=skip, limit=limit, session=session, order_by=order_by, order_desc=order_desc, search=search)


@router.get("/{user_id}", response_model=UserRead)
async def read_user_by_id(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    user = await service.get_user(user_id=user_id, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this user")

    target_user = await service.get_user(user_id=user_id, session=session)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to update not found")

    if not current_user.is_superuser:
        if user_in.is_superuser is True: # Non-superuser trying to make someone (or themselves) a superuser
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot make user a superuser")
        if user_in.is_active is not None and user_in.is_active != target_user.is_active: # Non-superuser trying to change active status
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change active status")
        if user_in.email is not None and user_in.email != target_user.email:
            # If allowing email change by non-superusers, re-verification should be triggered.
            # For now, disallowing direct email change by non-superusers to simplify.
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non-superusers cannot change email addresses directly. Please contact support.")

    updated_user = await service.update_user(user_id=user_id, user_in=user_in, session=session)
    if not updated_user:
        # This case should ideally be covered by target_user check, but service method might have other reasons to fail
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update failed")

    # If email was changed by a superuser, and the new email is different from the target's old one:
    if user_in.email is not None and user_in.email != target_user.email and updated_user.email == user_in.email and current_user.is_superuser:
        if updated_user.is_email_verified or updated_user.email_verification_token:
            # Mark as unverified and clear old token data
            updated_user.is_email_verified = False
            updated_user.email_verification_token = None
            updated_user.email_verification_token_expires_at = None
            session.add(updated_user) # Add to session before commit
            await session.commit() # Commit this change first
            # Trigger new verification email process for the new email
            await service.request_email_verification(updated_user.email, session)
            await session.refresh(updated_user) # Refresh to get latest state for the response

    return UserRead.model_validate(updated_user)


@router.delete("/{user_id}", response_model=UserRead) # Or return status 204
async def delete_user_endpoint(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    deleted_user = await service.delete_user(user_id=user_id, session=session)
    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(deleted_user)


@router.post("/{user_id}/roles/{role_id}", response_model=UserRead)
async def assign_role_to_user_endpoint(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    user = await service.assign_role_to_user(user_id=user_id, role_id=role_id, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or Role not found")
    return UserRead.model_validate(user)


@router.delete("/{user_id}/roles/{role_id}", response_model=UserRead)
async def revoke_role_from_user_endpoint(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    user = await service.revoke_role_from_user(user_id=user_id, role_id=role_id, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or role not assigned")
    return UserRead.model_validate(user)

# --- Email Verification Endpoints ---

class EmailVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/request-verification-email", status_code=status.HTTP_202_ACCEPTED)
async def request_verification_email_endpoint(
    request_data: EmailVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    await service.request_email_verification(email=request_data.email, session=session)
    return {"message": "If an account with this email exists and is not yet verified, a verification email process has been initiated."}


@router.get("/verify-email/{token}", response_model=UserRead)
async def verify_email_endpoint(
    token: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    user = await service.verify_email(token=token, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used verification token.",
        )
    return UserRead.model_validate(user)

# --- Password Reset Endpoints ---

@router.post("/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset_endpoint(
    request_data: PasswordResetRequestSchema, # From app.schemas.auth
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    """
    Request a password reset for an account with the given email.
    Always returns 202 Accepted to prevent user enumeration.
    """
    await service.request_password_reset(email=request_data.email, session=session)
    return {"message": "If an account with this email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    request_data: NewPasswordSchema, # From app.schemas.auth
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
):
    """
    Reset password using a valid token and new password.
    """
    success = await service.reset_password_with_token(
        token=request_data.token,
        new_password=request_data.new_password,
        session=session
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used password reset token, or new password too weak.", # Added "too weak"
        )
    return {"message": "Password has been reset successfully."}
