import uuid
from typing import Annotated, Optional # Optional for query params
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.services.employee_service import EmployeeService
from app.schemas.hr_schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.schemas.common import Page
from app.core.dependencies import require_permission # For permission checks
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
service_dep = Depends(EmployeeService) # Shortcut for Annotated[EmployeeService, Depends(EmployeeService)]

@router.post(
    "/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("employee:create"))]
)
async def create_employee(
    employee_in: EmployeeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[EmployeeService, service_dep],
):
    logger.info(f"User requesting to create employee: {employee_in.email}")
    db_employee = await service.create_employee(employee_in=employee_in, session=session)
    if not db_employee:
        logger.error(f"Employee creation failed for email: {employee_in.email}. Possible reasons: Invalid department/designation ID, or User ID already linked.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create employee. Ensure department, designation, and user (if provided) exist, and user is not already linked to another employee."
        )
    # EmployeeRead schema expects department and designation to be populated.
    # Service's create_employee now returns the employee with relationships loaded via self.get_employee.
    return EmployeeRead.from_attributes(db_employee)

@router.get(
    "/",
    response_model=Page[EmployeeRead],
    dependencies=[Depends(require_permission("employee:read"))]
)
async def read_employees(
    skip: int = 0,
    limit: int = Query(default=10, ge=1, le=100),
    department_id: Optional[uuid.UUID] = Query(default=None, description="Filter by Department ID"),
    designation_id: Optional[uuid.UUID] = Query(default=None, description="Filter by Designation ID"),
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[EmployeeService, service_dep],
):
    logger.info(f"User requesting to fetch employees (paginated). Filters: dept_id={department_id}, desig_id={designation_id}")
    # The service's get_employees method already handles populating relationships for EmployeeRead.
    return await service.get_employees(
        skip=skip,
        limit=limit,
        session=session,
        department_id=department_id,
        designation_id=designation_id
    )

@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_permission("employee:read"))]
)
async def read_employee_by_id(
    employee_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)], # Session might not be needed if service handles all
    service: Annotated[EmployeeService, service_dep],
):
    logger.info(f"User requesting to fetch employee by ID: {employee_id}")
    employee = await service.get_employee(employee_id=employee_id, session=session)
    if not employee:
        logger.warning(f"Employee with ID {employee_id} not found when requested by user.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    # Service's get_employee method ensures relationships (dept, desig) are loaded.
    return EmployeeRead.from_attributes(employee)

@router.put(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_permission("employee:update"))]
)
async def update_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeeUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[EmployeeService, service_dep],
):
    logger.info(f"User requesting to update employee ID: {employee_id}")
    updated_employee = await service.update_employee(
        employee_id=employee_id, employee_in=employee_in, session=session
    )
    if not updated_employee:
        logger.warning(f"Update failed by user request: Employee with ID {employee_id} not found or update error (e.g., invalid FK, user_id conflict).")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Or 400 if it's a validation error from service
            detail="Employee not found or update failed due to invalid data (e.g., non-existent department/designation/user or user_id already linked)."
        )
    # Service's update_employee now returns the employee with relationships loaded.
    return EmployeeRead.from_attributes(updated_employee)

@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT, # Standard for successful DELETE
    dependencies=[Depends(require_permission("employee:delete"))]
)
async def delete_employee(
    employee_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[EmployeeService, service_dep],
):
    logger.info(f"User requesting to delete employee ID: {employee_id}")
    deleted_employee_obj = await service.delete_employee(employee_id=employee_id, session=session)
    if not deleted_employee_obj:
        logger.warning(f"Deletion by user request failed for employee ID: {employee_id}. Not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
