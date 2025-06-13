import uuid
from typing import Annotated # Annotated not used in this file, but good for consistency
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.department_service import DepartmentService
from app.schemas.hr_schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.common import Page
# from app.models.user import User # Not needed directly for current_user type hint if using Depends(require_permission(...))
from app.core.dependencies import require_permission
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
service_dep = Depends(DepartmentService) # Shortcut for Annotated[DepartmentService, Depends(DepartmentService)]

@router.post(
    "/",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("department:create"))] # Permission check
)
async def create_department(
    department_in: DepartmentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DepartmentService, service_dep],
    # current_user: Annotated[User, Depends(require_permission("department:create"))] # User is available via require_permission
):
    logger.info(f"User requesting to create department: {department_in.name}")
    # Note: Service layer should ideally handle uniqueness checks if not done by DB.
    db_department = await service.create_department(department_in=department_in, session=session)
    if not db_department:
        # This case might occur if service layer has validation that can return None (e.g., FK not found)
        # or if there's a race condition with uniqueness not caught by DB.
        # For simple name uniqueness, DB constraint is best.
        logger.error(f"Department creation failed for name: {department_in.name}. Service returned None.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Department with name '{department_in.name}' might already exist or other creation error.")
    return DepartmentRead.model_validate(db_department)

@router.get(
    "/",
    response_model=Page[DepartmentRead],
    dependencies=[Depends(require_permission("department:read"))]
)
async def read_departments(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DepartmentService, service_dep],
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
):
    logger.info("User requesting to fetch all departments (paginated).")
    return await service.get_departments(skip=skip, limit=limit, session=session)

@router.get(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=[Depends(require_permission("department:read"))]
)
async def read_department_by_id(
    department_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)], # Session might not be needed if service handles all
    service: Annotated[DepartmentService, service_dep],
):
    logger.info(f"User requesting to fetch department by ID: {department_id}")
    department = await service.get_department(department_id=department_id, session=session)
    if not department:
        logger.warning(f"Department with ID {department_id} not found when requested by user.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return DepartmentRead.model_validate(department)

@router.put(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=[Depends(require_permission("department:update"))]
)
async def update_department(
    department_id: uuid.UUID,
    department_in: DepartmentUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DepartmentService, service_dep],
):
    logger.info(f"User requesting to update department ID: {department_id}")
    updated_department = await service.update_department(
        department_id=department_id, department_in=department_in, session=session
    )
    if not updated_department:
        logger.warning(f"Update failed by user request: Department with ID {department_id} not found or update error.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found or update failed due to validation error (e.g., name conflict).")
    return DepartmentRead.model_validate(updated_department)

@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT, # Standard for successful DELETE with no body
    dependencies=[Depends(require_permission("department:delete"))]
)
async def delete_department(
    department_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DepartmentService, service_dep],
):
    logger.info(f"User requesting to delete department ID: {department_id}")
    deleted_department_obj = await service.delete_department(department_id=department_id, session=session)
    if not deleted_department_obj:
        logger.warning(f"Deletion by user request failed for department ID: {department_id}. Not found or restricted.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found or deletion restricted (e.g., has employees).")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
