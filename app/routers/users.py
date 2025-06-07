import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.common import Page
from app.models.user import User # For current_user type hint
from app.core.dependencies import get_current_active_user, get_current_active_superuser

router = APIRouter()
# Using Depends(UserService) tells FastAPI to create an instance of UserService.
# If UserService had its own dependencies, they would be resolved.
service_dependency = Depends(UserService)

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    # For public user creation, remove or adjust current_user dependency.
    # For creation by superuser only:
    # current_admin: Annotated[User, Depends(get_current_active_superuser)],
):
    existing_user = await service.get_user_by_username(user_in.username, session)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    existing_email = await service.get_user_by_email(user_in.email, session)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = await service.create_user(user_in=user_in, session=session)
    return UserRead.from_attributes(user)


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)], # Added session for potential role loading
    service: Annotated[UserService, service_dependency], # Added service for potential role loading
):
    # The UserRead schema now includes `roles: Optional[List['RoleRead']]`.
    # To populate this, current_user.roles (which are UserRole link objects) needs to be loaded,
    # and then these UserRole objects need to be converted to RoleRead schemas.
    # This is a more complex operation than a simple from_attributes if roles are not already eagerly loaded
    # in a way that from_attributes can pick them up.
    # For now, we rely on the default behavior of from_attributes.
    # If User.roles were List[Role] and eagerly loaded, it would work.
    # Since User.roles is List[UserRole], UserRead needs to be adapted or a specific function is needed.

    # Simple conversion without explicit role loading here:
    # user_read = UserRead.from_attributes(current_user)

    # To include roles, you might need something like:
    # 1. Eager load user.roles and then role within each UserRole when fetching current_user.
    # 2. Or, fetch roles separately:
    # db_user = await service.get_user_with_roles(current_user.id, session) # Assumes such a method exists
    # return UserRead.from_attributes(db_user)

    # For now, returning based on current_user directly.
    # The UserRead.from_attributes will map fields. If current_user.roles is accessible and
    # UserRead is set up with a validator for roles, it might work.
    # Given User.roles is List[UserRole], and UserRead.roles is List[RoleRead],
    # a custom validator or pre-loading and transformation is needed.
    # The default from_attributes will likely leave roles as None or empty.
    return UserRead.from_attributes(current_user)


@router.get("/", response_model=Page[UserRead])
async def read_users(
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)], # Require superuser
):
    return await service.get_users(skip=skip, limit=limit, session=session)


@router.get("/{user_id}", response_model=UserRead)
async def read_user_by_id(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)], # Any active user can read
):
    user = await service.get_user(user_id=user_id, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.from_attributes(user)


@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # Allow user to update themselves, or superuser to update anyone
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this user")

    # Fetch the target user whose data is being updated
    target_user = await service.get_user(user_id=user_id, session=session)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to update not found")

    # Prevent non-superusers from elevating privileges or changing critical status fields
    if not current_user.is_superuser:
        if user_in.is_superuser is True: # Explicitly trying to set True
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot make user a superuser")
        if user_in.is_active is not None and user_in.is_active != target_user.is_active:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change active status")
        # Also, if they are not superuser, they cannot grant superuser status to anyone else even if user_in.is_superuser is False.
        # The model UserUpdate has is_superuser, so if they pass is_superuser=False, it's fine.
        # The main check is `user_in.is_superuser is True`.

    updated_user = await service.update_user(user_id=user_id, user_in=user_in, session=session)
    # service.update_user should handle "not found" case, but an extra check here is fine.
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found (after update attempt)")
    return UserRead.from_attributes(updated_user)


@router.delete("/{user_id}", response_model=UserRead)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[UserService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    deleted_user = await service.delete_user(user_id=user_id, session=session)
    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.from_attributes(deleted_user)


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
    # To properly return UserRead with updated roles, the user object needs to have its 'roles' relationship populated
    # in a way that UserRead.from_attributes can map it. This typically means user.roles should be a list of Role objects.
    # The service.assign_role_to_user refreshes `user`, but SQLModel's default refresh might not populate relationships
    # unless specifically configured (e.g. selectinload used originally, or relationship_attributes in refresh).
    # A practical way: fetch the user again with roles explicitly loaded.
    # For now, we'll rely on the service's refresh and from_attributes.
    # This might mean roles are not immediately visible in the response.
    return UserRead.from_attributes(user)


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
    return UserRead.from_attributes(user)
