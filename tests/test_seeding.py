import pytest
from typing import Set, Optional # Added Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select # For direct queries

from app.db.seed import seed_initial_data
from app.core.config import settings
from app.core.initial_data_config import (
    DEFAULT_SUPERUSER_EMAIL,
    DEFAULT_SUPERUSER_USERNAME,
    ROLES_CONFIG,
    ALL_PERMISSIONS
)
from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import UserRole # For checking superuser role assignment

# Ensure DEFAULT_SUPERUSER_PASSWORD is set for tests, e.g., in pytest.ini or environment
# The test will skip if the seeder cannot create the superuser due to missing password.

@pytest.mark.asyncio
async def test_initial_data_seeding(
    db_session: AsyncSession, # Uses the test DB with migrations applied
    user_service: UserService, # Fixture from conftest.py
    role_service: RoleService, # Fixture from conftest.py
    permission_service: PermissionService # Fixture from conftest.py
):
    """
    Tests the seed_initial_data function to ensure it populates the database
    with default permissions, roles, role-permission assignments, and a superuser.
    """
    # 1. Run the seeder function
    if not settings.DEFAULT_SUPERUSER_PASSWORD:
        pytest.skip("DEFAULT_SUPERUSER_PASSWORD not set in environment, skipping seeder test that requires it.")
        return

    await seed_initial_data(db_session)

    # 2. Verify Permissions
    all_config_perm_names = {p["name"] for p in ALL_PERMISSIONS}

    all_db_perms_result = await db_session.exec(select(Permission))
    db_permissions_list = all_db_perms_result.all()
    db_permission_names: Set[str] = {p.name for p in db_permissions_list}

    assert len(all_config_perm_names) == len(db_permissions_list), \
        f"Mismatch in number of permissions seeded. Config: {len(all_config_perm_names)}, DB: {len(db_permissions_list)}"
    for perm_name in all_config_perm_names:
        assert perm_name in db_permission_names, f"Permission '{perm_name}' from config was not found in the database."

    # 3. Verify Roles and their assigned permissions
    # We will check existence of key roles and spot-check some permission assignments.

    for role_config in ROLES_CONFIG:
        role_name_config = role_config["name"]
        db_role = await role_service.get_role_by_name(role_name_config, db_session)
        assert db_role is not None, f"Role '{role_name_config}' not found in DB."

        # Spot check permissions for this role
        # This requires a service method to get permissions for a role, or a direct query.
        # Let's implement a direct query for this test for now.
        role_permissions_stmt = (
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == db_role.id)
        )
        role_perms_result = await db_session.exec(role_permissions_stmt)
        db_role_perm_names: Set[str] = set(role_perms_result.all())

        config_role_perm_names: Set[str] = set(role_config.get("permissions", []))
        assert db_role_perm_names == config_role_perm_names, \
            f"Permission mismatch for role '{role_name_config}'. DB: {db_role_perm_names}, Config: {config_role_perm_names}"

    # 4. Verify Default Superuser
    superuser_db = await user_service.get_user_by_email(DEFAULT_SUPERUSER_EMAIL, db_session)
    assert superuser_db is not None, f"Default superuser with email {DEFAULT_SUPERUSER_EMAIL} not found."
    assert superuser_db.username == DEFAULT_SUPERUSER_USERNAME
    assert superuser_db.is_superuser is True
    assert superuser_db.is_active is True
    assert superuser_db.is_email_verified is True # Seeder should set this

    # Verify superuser has the "System Administrator" role
    sys_admin_role_db = await role_service.get_role_by_name("System Administrator", db_session)
    assert sys_admin_role_db is not None, "'System Administrator' role not found for superuser check."

    user_role_link_stmt = select(UserRole).where(
        UserRole.user_id == superuser_db.id,
        UserRole.role_id == sys_admin_role_db.id
    )
    user_role_link_result = await db_session.exec(user_role_link_stmt)
    assert user_role_link_result.first() is not None, \
        f"Superuser '{DEFAULT_SUPERUSER_USERNAME}' is not assigned the 'System Administrator' role."

    pytest.
