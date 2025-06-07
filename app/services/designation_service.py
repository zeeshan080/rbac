import uuid
from typing import List, Optional # List not used currently, but for consistency

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.hr_models import Designation # Correct model import
from app.schemas.hr_schemas import DesignationCreate, DesignationRead, DesignationUpdate
from app.schemas.common import Page
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class DesignationService:
    async def create_designation(self, designation_in: DesignationCreate, session: AsyncSession) -> Designation:
        logger.info(f"Creating new designation: {designation_in.title}")
        # Using model_validate for SQLModel (as it's also a Pydantic model)
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
            return None
        return designation

    async def get_designations(
        self, skip: int, limit: int, session: AsyncSession
    ) -> Page[DesignationRead]:
        logger.debug(f"Fetching designations: skip={skip}, limit={limit}")
        statement = select(Designation).offset(skip).limit(limit)
        count_statement = select(func.count()).select_from(Designation)

        results = await session.exec(statement)
        designations = results.all()

        total_count_result = await session.exec(count_statement)
        total = total_count_result.scalar_one_or_none() or 0 # Ensure total is int

        designations_read = [DesignationRead.from_attributes(desig) for desig in designations]
        return Page[DesignationRead](items=designations_read, total=total, page=(skip // limit) + 1 if limit > 0 else 1, size=limit)

    async def update_designation(
        self, designation_id: uuid.UUID, designation_in: DesignationUpdate, session: AsyncSession
    ) -> Optional[Designation]:
        logger.info(f"Updating designation with ID: {designation_id}")
        db_designation = await session.get(Designation, designation_id)
        if not db_designation:
            logger.warning(f"Update failed: Designation with ID {designation_id} not found.")
            return None

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

        # Similar check for employees with this designation could be added here.
        await session.delete(db_designation)
        await session.commit()
        logger.info(f"Designation '{db_designation.title}' (ID: {db_designation.id}) deleted successfully.")
        return db_designation
