import uuid
from typing import Annotated, List # List is not used directly
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.permission_service import PermissionService
from app.schemas.permission import PermissionCreate, PermissionRead, PermissionUpdate
from app.schemas.common import Page
from app.models.user import User # For current_user type hint
from app.core.dependencies import get_current_active_user, get_current_active_superuser

router = APIRouter()
service_dependency = Depends(PermissionService)

@router.post("/", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission_endpoint(
    permission_in: PermissionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[PermissionService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    existing_perm = await service.get_permission_by_name(permission_in.name, session)
    if existing_perm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission name already exists")
    permission = await service.create_permission(permission_in=permission_in, session=session)
    return PermissionRead.from_attributes(permission)

@router.get("/", response_model=Page[PermissionRead])
async def read_permissions_endpoint(
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[PermissionService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await service.get_permissions(skip=skip, limit=limit, session=session)

@router.get("/{permission_id}", response_model=PermissionRead)
async def read_permission_by_id_endpoint(
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[PermissionService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    permission = await service.get_permission(permission_id=permission_id, session=session)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return PermissionRead.from_attributes(permission)

@router.put("/{permission_id}", response_model=PermissionRead)
async def update_permission_endpoint(
    permission_id: uuid.UUID,
    permission_in: PermissionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[PermissionService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    updated_perm = await service.update_permission(permission_id=permission_id, permission_in=permission_in, session=session)
    if not updated_perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return PermissionRead.from_attributes(updated_perm)

@router.delete("/{permission_id}", response_model=PermissionRead)
async def delete_permission_endpoint(
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[PermissionService, service_dependency],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    deleted_perm = await service.delete_permission(permission_id=permission_id, session=session)
    if not deleted_perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return PermissionRead.from_attributes(deleted_perm)
