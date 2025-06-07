import uuid
from typing import Annotated # Not used directly, but for consistency with other router files
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.designation_service import DesignationService
from app.schemas.hr_schemas import DesignationCreate, DesignationRead, DesignationUpdate
from app.schemas.common import Page
from app.core.dependencies import require_permission
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
service_dep = Depends(DesignationService)

@router.post(
    "/",
    response_model=DesignationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("designation:create"))]
)
async def create_designation(
    designation_in: DesignationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DesignationService, service_dep],
):
    logger.info(f"User requesting to create designation: {designation_in.title}")
    # Service layer should ideally handle uniqueness checks for title if not done by DB
    db_designation = await service.create_designation(designation_in=designation_in, session=session)
    if not db_designation:
        logger.error(f"Designation creation failed for title: {designation_in.title}. Service returned None.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Designation with title '{designation_in.title}' might already exist or other creation error.")
    return DesignationRead.from_attributes(db_designation)

@router.get(
    "/",
    response_model=Page[DesignationRead],
    dependencies=[Depends(require_permission("designation:read"))]
)
async def read_designations(
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DesignationService, service_dep],
):
    logger.info("User requesting to fetch all designations (paginated).")
    return await service.get_designations(skip=skip, limit=limit, session=session)

@router.get(
    "/{designation_id}",
    response_model=DesignationRead,
    dependencies=[Depends(require_permission("designation:read"))]
)
async def read_designation_by_id(
    designation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)], # Session might not be needed if service handles all
    service: Annotated[DesignationService, service_dep],
):
    logger.info(f"User requesting to fetch designation by ID: {designation_id}")
    designation = await service.get_designation(designation_id=designation_id, session=session)
    if not designation:
        logger.warning(f"Designation with ID {designation_id} not found when requested by user.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designation not found")
    return DesignationRead.from_attributes(designation)

@router.put(
    "/{designation_id}",
    response_model=DesignationRead,
    dependencies=[Depends(require_permission("designation:update"))]
)
async def update_designation(
    designation_id: uuid.UUID,
    designation_in: DesignationUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DesignationService, service_dep],
):
    logger.info(f"User requesting to update designation ID: {designation_id}")
    updated_designation = await service.update_designation(
        designation_id=designation_id, designation_in=designation_in, session=session
    )
    if not updated_designation:
        logger.warning(f"Update failed by user request: Designation with ID {designation_id} not found or update error.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designation not found or update failed due to validation error (e.g., title conflict).")
    return DesignationRead.from_attributes(updated_designation)

@router.delete(
    "/{designation_id}",
    status_code=status.HTTP_204_NO_CONTENT, # Standard for successful DELETE
    dependencies=[Depends(require_permission("designation:delete"))]
)
async def delete_designation(
    designation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[DesignationService, service_dep],
):
    logger.info(f"User requesting to delete designation ID: {designation_id}")
    deleted_designation_obj = await service.delete_designation(designation_id=designation_id, session=session)
    if not deleted_designation_obj:
        logger.warning(f"Deletion by user request failed for designation ID: {designation_id}. Not found or restricted.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designation not found or deletion restricted (e.g., has employees).")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
