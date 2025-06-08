import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession # Explicitly using SQLAlchemy's AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hr_models import Employee, Department, Designation
from app.models.user import User
from app.schemas.hr_schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class EmployeeService:
    async def create_employee(self, employee_in: EmployeeCreate, session: AsyncSession) -> Optional[Employee]:
        logger.info(f"Creating new employee: {employee_in.first_name} {employee_in.last_name} ({employee_in.email})")

        if employee_in.department_id:
            dept = await session.get(Department, employee_in.department_id)
            if not dept:
                logger.error(f"Create employee failed: Department with ID {employee_in.department_id} not found.")
                return None
        if employee_in.designation_id:
            desig = await session.get(Designation, employee_in.designation_id)
            if not desig:
                logger.error(f"Create employee failed: Designation with ID {employee_in.designation_id} not found.")
                return None
        if employee_in.user_id:
            usr = await session.get(User, employee_in.user_id)
            if not usr:
                logger.error(f"Create employee failed: User with ID {employee_in.user_id} not found.")
                return None
            existing_employee_for_user_stmt = select(Employee).where(Employee.user_id == employee_in.user_id)
            existing_employee_result_proxy = await session.execute(existing_employee_for_user_stmt)
            if existing_employee_result_proxy.scalars().first():
                logger.error(f"Create employee failed: User ID {employee_in.user_id} is already linked to another employee.")
                return None

        db_employee = Employee.model_validate(employee_in)
        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee)

        logger.info(f"Employee '{db_employee.first_name} {db_employee.last_name}' created successfully with ID: {db_employee.id}")
        return await self.get_employee(db_employee.id, session) # Return with relationships loaded


    async def get_employee(self, employee_id: uuid.UUID, session: AsyncSession) -> Optional[Employee]:
        logger.debug(f"Fetching employee with ID: {employee_id}")
        statement = (
            select(Employee)
            .where(Employee.id == employee_id)
            .options(selectinload(Employee.department), selectinload(Employee.designation))
        )
        result_proxy = await session.execute(statement)
        employee = result_proxy.scalars().first()

        if not employee:
            logger.warning(f"Employee with ID {employee_id} not found.")
        return employee

    async def get_employees(
        self,
        skip: int,
        limit: int,
        session: AsyncSession,
        department_id: Optional[uuid.UUID] = None,
        designation_id: Optional[uuid.UUID] = None
    ) -> Page[EmployeeRead]:
        logger.debug(f"Fetching employees: skip={skip}, limit={limit}, dept_id={department_id}, desig_id={designation_id}")

        statement = (
            select(Employee)
            .options(selectinload(Employee.department), selectinload(Employee.designation))
        )
        # Use Employee.id for count for clarity, though func.count() on table is fine
        count_statement = select(func.count(Employee.id))

        if department_id:
            statement = statement.where(Employee.department_id == department_id)
            count_statement = count_statement.where(Employee.department_id == department_id)
        if designation_id:
            statement = statement.where(Employee.designation_id == designation_id)
            count_statement = count_statement.where(Employee.designation_id == designation_id)

        statement = statement.offset(skip).limit(limit)

        employees_result_proxy = await session.execute(statement)
        employees = employees_result_proxy.scalars().all()

        total_count_result_proxy = await session.execute(count_statement)
        total = total_count_result_proxy.scalar_one_or_none() or 0

        employees_read = [EmployeeRead.from_attributes(emp) for emp in employees]
        logger.debug(f"Found {len(employees_read)} employees for current page, total {total}.")
        return Page[EmployeeRead](items=employees_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_employee(
        self, employee_id: uuid.UUID, employee_in: EmployeeUpdate, session: AsyncSession
    ) -> Optional[Employee]:
        logger.info(f"Updating employee with ID: {employee_id}")
        db_employee = await session.get(Employee, employee_id)
        if not db_employee:
            logger.warning(f"Update failed: Employee with ID {employee_id} not found.")
            return None

        update_data = employee_in.model_dump(exclude_unset=True)

        if "department_id" in update_data and update_data["department_id"] is not None:
            if update_data["department_id"] != db_employee.department_id:
                dept = await session.get(Department, update_data["department_id"])
                if not dept:
                    logger.error(f"Update employee failed: Department with ID {update_data['department_id']} not found.")
                    return None
        if "designation_id" in update_data and update_data["designation_id"] is not None:
            if update_data["designation_id"] != db_employee.designation_id:
                desig = await session.get(Designation, update_data["designation_id"])
                if not desig:
                    logger.error(f"Update employee failed: Designation with ID {update_data['designation_id']} not found.")
                    return None
        if "user_id" in update_data and update_data["user_id"] is not None:
            if update_data["user_id"] != db_employee.user_id:
                usr = await session.get(User, update_data["user_id"])
                if not usr:
                    logger.error(f"Update employee failed: User with ID {update_data['user_id']} not found.")
                    return None
                existing_employee_for_user_stmt = select(Employee).where(Employee.user_id == update_data["user_id"], Employee.id != employee_id)
                existing_employee_result_proxy = await session.execute(existing_employee_for_user_stmt)
                if existing_employee_result_proxy.scalars().first():
                    logger.error(f"Update employee failed: User ID {update_data['user_id']} is already linked to another employee.")
                    return None

        for key, value in update_data.items():
            setattr(db_employee, key, value)

        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee)

        return await self.get_employee(employee_id, session) # Re-fetch with relationships

    async def delete_employee(self, employee_id: uuid.UUID, session: AsyncSession) -> Optional[Employee]:
        logger.info(f"Deleting employee with ID: {employee_id}")
        db_employee = await self.get_employee(employee_id, session)
        if not db_employee:
            logger.warning(f"Delete failed: Employee with ID {employee_id} not found.")
            return None

        # Consider implications: what happens to related data like LeaveRequests?
        # If LeaveRequest.employee_id is non-nullable and has no ON DELETE rule, this will fail.
        # This should be handled by DB schema (CASCADE, SET NULL, RESTRICT) or by deleting/nullifying dependent records here.
        # For now, direct delete.
        await session.delete(db_employee)
        await session.commit()
        logger.info(f"Employee ID {employee_id} ({db_employee.first_name} {db_employee.last_name}) deleted successfully.")
        return db_employee
