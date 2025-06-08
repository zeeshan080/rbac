import uuid
from typing import List, Optional

from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession # Explicitly using SQLAlchemy's AsyncSession

from app.models.hr_models import Designation, Employee # Employee for delete check
from app.schemas.hr_schemas import DesignationCreate, DesignationRead, DesignationUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger
# from fastapi import HTTPException, status # For raising error on delete if dependent items exist

logger = get_logger(__name__)

class DesignationService:
    async def create_designation(self, designation_in: DesignationCreate, session: AsyncSession) -> Optional[Designation]:
        logger.info(f"Creating new designation: {designation_in.title}")

        # Check if designation title already exists
        existing_desig_stmt = select(Designation).where(Designation.title == designation_in.title)
        existing_desig_proxy = await session.execute(existing_desig_stmt)
        if existing_desig_proxy.scalars().first():
            logger.warning(f"Designation creation failed: Title '{designation_in.title}' already exists.")
            return None # Indicate failure

        # SQLModel fields default to None if not provided in schema and not required by model
        # Using model_validate for SQLModel as it inherits from Pydantic BaseModel
        db_designation = Designation.model_validate(designation_in)

        session.add(db_designation)
        await session.commit()
        await session.refresh(db_designation)
        logger.info(f"Designation '{db_designation.title}' created successfully with ID: {db_designation.id}")
        return db_designation

    async def get_designation(self, designation_id: uuid.UUID, session: AsyncSession) -> Optional[Designation]:
        logger.debug(f"Fetching designation with ID: {designation_id}")
        designation = await session.get(Designation, designation_id)
        if not designation:
            logger.warning(f"Designation with ID {designation_id} not found.")
        return designation

    async def get_designation_by_title(self, title: str, session: AsyncSession) -> Optional[Designation]: # Added method
        logger.debug(f"Fetching designation by title: {title}")
        statement = select(Designation).where(Designation.title == title)
        result_proxy = await session.execute(statement)
        designation = result_proxy.scalars().first()
        if not designation:
            logger.debug(f"Designation with title '{title}' not found.")
        return designation


    async def get_designations(
        self, skip: int, limit: int, session: AsyncSession
    ) -> Page[DesignationRead]:
        logger.debug(f"Fetching designations: skip={skip}, limit={limit}")

        statement = select(Designation).offset(skip).limit(limit)
        count_statement = select(func.count(Designation.id)).select_from(Designation)

        designations_result_proxy = await session.execute(statement)
        designations = designations_result_proxy.scalars().all()

        total_count_result_proxy = await session.execute(count_statement)
        total = total_count_result_proxy.scalar_one_or_none() or 0

        designations_read = [DesignationRead.from_attributes(desig) for desig in designations]
        logger.debug(f"Found {len(designations_read)} designations for current page, total {total}.")
        return Page[DesignationRead](items=designations_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_designation(
        self, designation_id: uuid.UUID, designation_in: DesignationUpdate, session: AsyncSession
    ) -> Optional[Designation]:
        logger.info(f"Updating designation with ID: {designation_id}")
        db_designation = await session.get(Designation, designation_id)
        if not db_designation:
            logger.warning(f"Update failed: Designation with ID {designation_id} not found.")
            return None

        # Check for title conflict if title is being changed
        if designation_in.title is not None and designation_in.title != db_designation.title:
            existing_desig_stmt = select(Designation).where(Designation.title == designation_in.title, Designation.id != designation_id) # Exclude self
            existing_desig_proxy = await session.execute(existing_desig_stmt)
            if existing_desig_proxy.scalars().first():
                logger.warning(f"Designation update failed: Title '{designation_in.title}' already exists for another designation.")
                return None # Indicate failure

        update_data = designation_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_designation, key, value)

        session.add(db_designation)
        await session.commit()
        await session.refresh(db_designation)
        logger.info(f"Designation '{db_designation.title}' (ID: {db_designation.id}) updated successfully.")
        return db_designation

    async def delete_designation(self, designation_id: uuid.UUID, session: AsyncSession) -> Optional[Designation]:
        logger.info(f"Deleting designation with ID: {designation_id}")
        db_designation = await session.get(Designation, designation_id)
        if not db_designation:
            logger.warning(f"Delete failed: Designation with ID {designation_id} not found.")
            return None

        # Check for employees with this designation before deleting
        employee_count_stmt = select(func.count(Employee.id)).where(Employee.designation_id == designation_id)
        employee_count_proxy = await session.execute(employee_count_stmt)
        if employee_count_proxy.scalar_one() > 0:
            logger.error(f"Delete failed: Designation {db_designation.title} (ID: {designation_id}) has {employee_count_proxy.scalar_one()} associated employees.")
            return None # Indicate failure due to dependencies

        await session.delete(db_designation)
        await session.commit()
        logger.info(f"Designation '{db_designation.title}' (ID: {db_designation.id}) deleted successfully.")
        return db_designation
