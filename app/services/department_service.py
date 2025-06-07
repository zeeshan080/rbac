import uuid
from typing import List, Optional # List not used in this file currently but good for consistency

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
# Ensure SQLModelSelect is imported if used for type hinting specific select statements
# from sqlmodel.sql.expression import SelectOfScalar, Select # Not used in current version

from app.models.hr_models import Department # Correct model import
from app.schemas.hr_schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class DepartmentService:
    async def create_department(self, department_in: DepartmentCreate, session: AsyncSession) -> Department:
        logger.info(f"Creating new department: {department_in.name}")
        # Using model_validate for SQLModel (as it's also a Pydantic model)
        # This assumes DepartmentCreate schema fields are compatible with Department model fields.
        db_department = Department.model_validate(department_in)

        session.add(db_department)
        await session.commit()
        await session.refresh(db_department)
        logger.info(f"Department '{db_department.name}' created successfully with ID: {db_department.id}")
        return db_department

    async def get_department(self, department_id: uuid.UUID, session: AsyncSession) -> Optional[Department]:
        logger.debug(f"Fetching department with ID: {department_id}")
        department = await session.get(Department, department_id)
        if not department:
            logger.warning(f"Department with ID {department_id} not found.")
            return None
        return department

    async def get_departments(
        self, skip: int, limit: int, session: AsyncSession
    ) -> Page[DepartmentRead]:
        logger.debug(f"Fetching departments: skip={skip}, limit={limit}")

        statement = select(Department).offset(skip).limit(limit)
        # For counting, select(func.count(Department.id)) is more explicit if Department.id exists
        # or select(func.count()).select_from(Department) if table is clear
        count_statement = select(func.count()).select_from(Department)

        results = await session.exec(statement)
        departments = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one_or_none() or 0 # Ensure total is int, default to 0 if None

        departments_read = [DepartmentRead.from_attributes(dept) for dept in departments]

        return Page[DepartmentRead](items=departments_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_department(
        self, department_id: uuid.UUID, department_in: DepartmentUpdate, session: AsyncSession
    ) -> Optional[Department]:
        logger.info(f"Updating department with ID: {department_id}")
        db_department = await session.get(Department, department_id)
        if not db_department:
            logger.warning(f"Update failed: Department with ID {department_id} not found.")
            return None

        update_data = department_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_department, key, value)

        session.add(db_department)
        await session.commit()
        await session.refresh(db_department)
        logger.info(f"Department '{db_department.name}' (ID: {db_department.id}) updated successfully.")
        return db_department

    async def delete_department(self, department_id: uuid.UUID, session: AsyncSession) -> Optional[Department]:
        logger.info(f"Deleting department with ID: {department_id}")
        db_department = await session.get(Department, department_id)
        if not db_department:
            logger.warning(f"Delete failed: Department with ID {department_id} not found.")
            return None

        # Note: The script included a commented-out check for employees.
        # This would require importing Employee model and potentially raising an HTTPException or returning an error.
        # For now, direct delete as per script's active lines.
        # from app.models.hr_models import Employee # Would be needed for the check
        # employee_count_stmt = select(func.count(Employee.id)).where(Employee.department_id == department_id)
        # employee_count_res = await session.exec(employee_count_stmt)
        # if employee_count_res.scalar_one_or_none() > 0: # Check for > 0
        #     logger.error(f"Delete failed: Department {db_department.name} (ID: {department_id}) has associated employees.")
        #     # raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete department with associated employees.")
        #     return None # Or some other indicator of failure due to dependencies

        await session.delete(db_department)
        await session.commit()
        logger.info(f"Department '{db_department.name}' (ID: {db_department.id}) deleted successfully.")
        return db_department
