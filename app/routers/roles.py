import uuid
from typing import Annotated, List # List is not used directly, but good for consistency
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.role_service import RoleService
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.schemas.common import Page
from app.models.user import User # For current_user type hint
from app.core.dependencies import get_current_active_user, get_current_active_superuser

router = APIRouter()
service_dependency = Depends(RoleService)

@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role_endpoint(
    role_in: RoleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    existing_role = await service.get_role_by_name(role_in.name, session)
    if existing_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already exists")
    role = await service.create_role(role_in=role_in, session=session)
    return RoleRead.from_attributes(role)

@router.get("/", response_model=Page[RoleRead])
async def read_roles_endpoint(
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await service.get_roles(skip=skip, limit=limit, session=session)

@router.get("/{role_id}", response_model=RoleRead)
async def read_role_by_id_endpoint(
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    role = await service.get_role(role_id=role_id, session=session)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleRead.from_attributes(role)

@router.put("/{role_id}", response_model=RoleRead)
async def update_role_endpoint(
    role_id: uuid.UUID,
    role_in: RoleUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    updated_role = await service.update_role(role_id=role_id, role_in=role_in, session=session)
    if not updated_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleRead.from_attributes(updated_role)

@router.delete("/{role_id}", response_model=RoleRead)
async def delete_role_endpoint(
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    deleted_role = await service.delete_role(role_id=role_id, session=session)
    if not deleted_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleRead.from_attributes(deleted_role)

@router.post("/{role_id}/permissions/{permission_id}", response_model=RoleRead)
async def assign_permission_to_role_endpoint(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    role = await service.assign_permission_to_role(role_id=role_id, permission_id=permission_id, session=session)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role or Permission not found")
    # Similar to UserRead.roles, RoleRead.permissions may not be immediately populated in the response
    # without specific handling for loading/refreshing the 'permissions' relationship.
    return RoleRead.from_attributes(role)

@router.delete("/{role_id}/permissions/{permission_id}", response_model=RoleRead)
async def revoke_permission_from_role_endpoint(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[RoleService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    role = await service.revoke_permission_from_role(role_id=role_id, permission_id=permission_id, session=session)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or permission not assigned")
    return RoleRead.from_attributes(role)
