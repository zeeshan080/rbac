import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession # Explicitly using SQLAlchemy's AsyncSession

from app.models.hr_models import Department, Employee # Employee for delete check
from app.schemas.hr_schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger
# from fastapi import HTTPException, status # For raising error on delete if dependent items exist

logger = get_logger(__name__)

class DepartmentService:
    async def create_department(self, department_in: DepartmentCreate, session: AsyncSession) -> Optional[Department]: # Return Optional for validation
        logger.info(f"Creating new department: {department_in.name}")

        # Check if department name already exists
        existing_dept_stmt = select(Department).where(Department.name == department_in.name)
        existing_dept_proxy = await session.execute(existing_dept_stmt)
        if existing_dept_proxy.scalars().first():
            logger.warning(f"Department creation failed: Name '{department_in.name}' already exists.")
            return None # Indicate failure due to name conflict

        # SQLModel fields default to None if not provided in schema and not required by model
        # Using model_validate for SQLModel as it inherits from Pydantic BaseModel
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
        return department

    async def get_departments(
        self, skip: int, limit: int, session: AsyncSession
    ) -> Page[DepartmentRead]:
        logger.debug(f"Fetching departments: skip={skip}, limit={limit}")

        statement = select(Department).offset(skip).limit(limit)
        count_statement = select(func.count(Department.id)).select_from(Department)

        departments_result_proxy = await session.execute(statement)
        departments = departments_result_proxy.scalars().all()

        total_count_result_proxy = await session.execute(count_statement)
        total = total_count_result_proxy.scalar_one_or_none() or 0

        departments_read = [DepartmentRead.from_attributes(dept) for dept in departments]
        logger.debug(f"Found {len(departments_read)} departments for current page, total {total}.")
        return Page[DepartmentRead](items=departments_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_department(
        self, department_id: uuid.UUID, department_in: DepartmentUpdate, session: AsyncSession
    ) -> Optional[Department]:
        logger.info(f"Updating department with ID: {department_id}")
        db_department = await session.get(Department, department_id)
        if not db_department:
            logger.warning(f"Update failed: Department with ID {department_id} not found.")
            return None

        # Check for name conflict if name is being changed
        if department_in.name is not None and department_in.name != db_department.name:
            existing_dept_stmt = select(Department).where(Department.name == department_in.name, Department.id != department_id) # Exclude self
            existing_dept_proxy = await session.execute(existing_dept_stmt)
            if existing_dept_proxy.scalars().first():
                logger.warning(f"Department update failed: Name '{department_in.name}' already exists for another department.")
                return None # Indicate failure due to name conflict

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

        # Check for employees in this department before deleting
        employee_count_stmt = select(func.count(Employee.id)).where(Employee.department_id == department_id)
        employee_count_proxy = await session.execute(employee_count_stmt)
        if employee_count_proxy.scalar_one() > 0:
            logger.error(f"Delete failed: Department {db_department.name} (ID: {department_id}) has {employee_count_proxy.scalar_one()} associated employees.")
            return None # Indicate failure due to dependencies

        await session.delete(db_department)
        await session.commit()
        logger.info(f"Department '{db_department.name}' (ID: {db_department.id}) deleted successfully.")
        return db_department
