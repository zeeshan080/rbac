import asyncio
from typing import Dict, Any, Optional # Added Optional for type hints

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging_config import get_logger
from app.core.config import settings
from app.core.initial_data_config import (
    ALL_PERMISSIONS,
    ROLES_CONFIG,
    DEFAULT_SUPERUSER_EMAIL,
    DEFAULT_SUPERUSER_USERNAME,
)
from app.database import AsyncSessionLocal # Use the session factory for standalone script
from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.schemas.user import UserCreate
from app.schemas.role import RoleCreate
from app.schemas.permission import PermissionCreate
from app.models.role import Role # For type hinting
from app.models.permission import Permission # For type hinting
# User model is implicitly used via UserService

logger = get_logger(__name__)

async def seed_initial_data(db_session: AsyncSession):
    logger.info("Starting initial data seeding...")

    user_service = UserService()
    role_service = RoleService()
    permission_service = PermissionService()

    # 1. Seed Permissions
    logger.info("Seeding permissions...")
    created_permissions: Dict[str, Permission] = {}
    for perm_data in ALL_PERMISSIONS:
        perm_name = perm_data["name"]
        existing_perm = await permission_service.get_permission_by_name(name=perm_name, session=db_session)
        if not existing_perm:
            perm_in = PermissionCreate(name=perm_name, description=perm_data.get("description"))
            created_perm = await permission_service.create_permission(permission_in=perm_in, session=db_session)
            if created_perm:
                logger.info(f"Created permission: {perm_name}")
                created_permissions[perm_name] = created_perm
            else:
                logger.error(f"Failed to create permission: {perm_name}")
        else:
            logger.info(f"Permission '{perm_name}' already exists.")
            created_permissions[perm_name] = existing_perm
    logger.info("Permissions seeding complete.")

    # 2. Seed Roles and Assign Permissions
    logger.info("Seeding roles and assigning permissions...")
    created_roles: Dict[str, Role] = {}
    for role_data in ROLES_CONFIG:
        role_name = role_data["name"]
        existing_role = await role_service.get_role_by_name(name=role_name, session=db_session)
        current_role: Optional[Role] = None # Ensure current_role is defined before assignment
        if not existing_role:
            role_in = RoleCreate(name=role_name, description=role_data.get("description"))
            created_role = await role_service.create_role(role_in=role_in, session=db_session)
            if created_role:
                logger.info(f"Created role: {role_name}")
                current_role = created_role
            else:
                logger.error(f"Failed to create role: {role_name}")
                continue
        else:
            logger.info(f"Role '{role_name}' already exists.")
            current_role = existing_role

        if current_role:
            created_roles[role_name] = current_role
            # Check if permissions need to be assigned/updated even if role exists
            # For simplicity, we assign if role was just created or if we want to ensure all perms are there.
            # The assign_permission_to_role in service should be idempotent.
            for perm_name in role_data.get("permissions", []):
                permission_obj = created_permissions.get(perm_name)
                if permission_obj:
                    updated_role_with_perm = await role_service.assign_permission_to_role(
                        role_id=current_role.id, permission_id=permission_obj.id, session=db_session
                    )
                    if updated_role_with_perm:
                         logger.debug(f"Ensured permission '{perm_name}' is assigned to role '{role_name}'.")
                else:
                    logger.warning(f"Permission '{perm_name}' not found in created_permissions for role '{role_name}'. Skipping assignment.")
    logger.info("Roles and permissions assignment complete.")

    # 3. Seed Default Superuser
    logger.info("Seeding default superuser...")
    if not settings.DEFAULT_SUPERUSER_PASSWORD:
        logger.error("DEFAULT_SUPERUSER_PASSWORD environment variable not set. Cannot create superuser.")
    else:
        # Check by email first, then by username if email not found (or vice-versa)
        # This handles cases where one might exist but not the other, though ideally they are unique together.
        superuser = await user_service.get_user_by_email(email=DEFAULT_SUPERUSER_EMAIL, session=db_session)
        if not superuser:
            superuser = await user_service.get_user_by_username(username=DEFAULT_SUPERUSER_USERNAME, session=db_session)

        if not superuser:
            superuser_in = UserCreate(
                username=DEFAULT_SUPERUSER_USERNAME,
                email=DEFAULT_SUPERUSER_EMAIL,
                password=settings.DEFAULT_SUPERUSER_PASSWORD,
                is_active=True,
                is_superuser=True,
                # is_email_verified is False by default in User model.
            )
            superuser = await user_service.create_user(user_in=superuser_in, session=db_session)
            if superuser:
                logger.info(f"Created default superuser: {superuser.username} ({superuser.email})")
                # Mark email as verified for the superuser
                if not superuser.is_email_verified:
                    superuser.is_email_verified = True
                    # db_session.add(superuser) # UserService.create_user already adds and refreshes
                    # await db_session.commit()
                    # await db_session.refresh(superuser)
                    # The above is not needed if update_user is called, or if service handles it.
                    # Let's use an update call for clarity or do it directly.
                    # For simplicity, directly update and commit here.
                    logger.info(f"Marking email for superuser {superuser.username} as verified.")
                    db_session.add(superuser) # Add to session again if modified

                # Assign "System Administrator" role
                admin_role = created_roles.get("System Administrator")
                if admin_role:
                    await user_service.assign_role_to_user(user_id=superuser.id, role_id=admin_role.id, session=db_session)
                    logger.info(f"Assigned 'System Administrator' role to superuser {superuser.username}.")
                else:
                    logger.warning("Could not find 'System Administrator' role to assign to superuser.")

                await db_session.commit() # Commit email verification and role assignment
                await db_session.refresh(superuser) # Ensure superuser object has latest state
            else:
                logger.error(f"Failed to create default superuser with email {DEFAULT_SUPERUSER_EMAIL}.")
        else:
            logger.info(f"Default superuser with email '{DEFAULT_SUPERUSER_EMAIL}' or username '{DEFAULT_SUPERUSER_USERNAME}' already exists.")
            # Optionally, ensure superuser status and role assignment if user exists but isn't fully configured
            if not superuser.is_superuser:
                superuser.is_superuser = True
                logger.info(f"Made existing user {superuser.username} a superuser.")
                db_session.add(superuser)
            if not superuser.is_email_verified: # Also verify email if not already
                 superuser.is_email_verified = True
                 logger.info(f"Marked email for existing user {superuser.username} as verified.")
                 db_session.add(superuser)
            admin_role = created_roles.get("System Administrator")
            if admin_role:
                # Check if role is already assigned before attempting to assign
                # This might require fetching user with roles or checking UserRole table.
                # For simplicity, assign_role_to_user should be idempotent.
                await user_service.assign_role_to_user(user_id=superuser.id, role_id=admin_role.id, session=db_session)
                logger.info(f"Ensured 'System Administrator' role is assigned to existing superuser {superuser.username}.")
            await db_session.commit()


    logger.info("Initial data seeding process finished.")

# This part is for standalone execution of the script
async def main():
    logger.info("Initiating standalone database session for seeding.")
    # It's important that env vars (like DATABASE_URL, DEFAULT_SUPERUSER_PASSWORD) are loaded
    # when this script runs. Pydantic's settings object should handle .env loading.
    async with AsyncSessionLocal() as session: # Use the factory to create a session
        try:
            await seed_initial_data(session)
            # The services commit their own main operations.
            # A final commit here can be useful for any direct changes made in seed_initial_data
            # like setting is_email_verified on superuser if not done via service.
            # await session.commit()
        except Exception as e:
            logger.error(f"An error occurred during data seeding: {e}", exc_info=True)
            await session.rollback() # Rollback on any error during the seeding process
        finally:
            await session.close() # Ensure session is closed

if __name__ == "__main__":
    # This allows running the script directly, e.g., python -m app.db.seed
    # Ensure PYTHONPATH is set correctly if running this way (e.g., export PYTHONPATH=.)
    # so that 'app.core', 'app.models' etc. can be imported.
    logger.info("Running seed script directly from __main__.")
    asyncio.run(main())
