import uuid
from typing import List, Optional # List is used by Page type hint

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload # For eager loading relationships

from app.models.hr_models import Employee, Department, Designation
from app.models.user import User
from app.schemas.hr_schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class EmployeeService:
    async def create_employee(self, employee_in: EmployeeCreate, session: AsyncSession) -> Optional[Employee]: # Return Optional for validation failures
        logger.info(f"Creating new employee: {employee_in.first_name} {employee_in.last_name} ({employee_in.email})")

        # Validate FKs if provided
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
            # Check if this user_id is already linked to another employee (due to unique constraint)
            existing_employee_for_user_stmt = select(Employee).where(Employee.user_id == employee_in.user_id)
            existing_employee_for_user_result = await session.exec(existing_employee_for_user_stmt)
            if existing_employee_for_user_result.first():
                logger.error(f"Create employee failed: User ID {employee_in.user_id} is already linked to another employee.")
                return None

        # SQLModel can create model instance from schema instance directly if fields match
        db_employee = Employee.model_validate(employee_in)
        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee)

        logger.info(f"Employee '{db_employee.first_name} {db_employee.last_name}' created successfully with ID: {db_employee.id}")
        # Return with relationships loaded to match get_employee behavior for consistency
        return await self.get_employee(db_employee.id, session)


    async def get_employee(self, employee_id: uuid.UUID, session: AsyncSession) -> Optional[Employee]:
        logger.debug(f"Fetching employee with ID: {employee_id}")
        statement = (
            select(Employee)
            .where(Employee.id == employee_id)
            .options(selectinload(Employee.department), selectinload(Employee.designation))
            # .options(selectinload(Employee.user)) # User data can be large; load only if EmployeeRead needs it
        )
        result = await session.exec(statement)
        employee = result.first()

        if not employee:
            logger.warning(f"Employee with ID {employee_id} not found.")
            return None
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
        count_statement = select(func.count(Employee.id)) # More specific count

        if department_id:
            statement = statement.where(Employee.department_id == department_id)
            count_statement = count_statement.where(Employee.department_id == department_id)
        if designation_id:
            statement = statement.where(Employee.designation_id == designation_id)
            count_statement = count_statement.where(Employee.designation_id == designation_id)

        statement = statement.offset(skip).limit(limit)

        results = await session.exec(statement)
        employees = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one_or_none() or 0

        employees_read = [EmployeeRead.from_attributes(emp) for emp in employees]

        return Page[EmployeeRead](items=employees_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_employee(
        self, employee_id: uuid.UUID, employee_in: EmployeeUpdate, session: AsyncSession
    ) -> Optional[Employee]:
        logger.info(f"Updating employee with ID: {employee_id}")
        # Fetch without relationships first, as we're updating scalar fields.
        # Relationships are handled by FKs in employee_in.
        db_employee = await session.get(Employee, employee_id)
        if not db_employee:
            logger.warning(f"Update failed: Employee with ID {employee_id} not found.")
            return None

        update_data = employee_in.model_dump(exclude_unset=True)

        # Validate FKs if they are being changed
        if "department_id" in update_data and update_data["department_id"] is not None:
            if update_data["department_id"] != db_employee.department_id: # Check if it's actually changing
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
            if update_data["user_id"] != db_employee.user_id: # Check if it's changing and not just resubmitted
                usr = await session.get(User, update_data["user_id"])
                if not usr:
                    logger.error(f"Update employee failed: User with ID {update_data['user_id']} not found.")
                    return None
                # Check unique constraint if user_id is changing to a new value
                existing_employee_for_user_stmt = select(Employee).where(Employee.user_id == update_data["user_id"], Employee.id != employee_id)
                existing_employee_for_user_result = await session.exec(existing_employee_for_user_stmt)
                if existing_employee_for_user_result.first():
                    logger.error(f"Update employee failed: User ID {update_data['user_id']} is already linked to another employee.")
                    return None

        for key, value in update_data.items():
            setattr(db_employee, key, value)

        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee) # Refresh scalar attributes

        # Return with relationships loaded to match get_employee behavior
        return await self.get_employee(employee_id, session)

    async def delete_employee(self, employee_id: uuid.UUID, session: AsyncSession) -> Optional[Employee]:
        logger.info(f"Deleting employee with ID: {employee_id}")
        # Fetch with relationships to return the full object before deletion, if desired by API
        # Or fetch without if only ID/status is needed for confirmation.
        # For consistency with get_employee, fetch with relationships.
        db_employee = await self.get_employee(employee_id, session)
        if not db_employee:
            logger.warning(f"Delete failed: Employee with ID {employee_id} not found.")
            return None

        await session.delete(db_employee)
        await session.commit()
        logger.info(f"Employee ID {employee_id} ({db_employee.first_name} {db_employee.last_name}) deleted successfully.")
        # db_employee still holds data but is detached.
        return db_employee
