# app/core/initial_data_config.py

# --- Default Superuser Configuration ---
# Password for the default superuser will be taken from DEFAULT_SUPERUSER_PASSWORD environment variable
DEFAULT_SUPERUSER_EMAIL = "admin@example.com"
DEFAULT_SUPERUSER_USERNAME = "admin"

# --- Permissions Configuration ---
# List of dictionaries: {"name": "permission:name", "description": "Description of permission"}

PERMISSIONS_ADMIN = [
    {"name": "admin:access", "description": "Grants access to administrative sections/dashboards."},
    {"name": "user:create", "description": "Allows creating new users."},
    {"name": "user:read", "description": "Allows reading user information."},
    {"name": "user:update", "description": "Allows updating user information."},
    {"name": "user:delete", "description": "Allows deleting users."},
    {"name": "user:manage_roles", "description": "Allows assigning/revoking roles for users."},

    {"name": "role:create", "description": "Allows creating new roles."},
    {"name": "role:read", "description": "Allows reading role information."},
    {"name": "role:update", "description": "Allows updating role information."},
    {"name": "role:delete", "description": "Allows deleting roles."},
    {"name": "role:manage_permissions", "description": "Allows assigning/revoking permissions for roles."},

    {"name": "permission:create", "description": "Allows creating new permissions (use with caution)."},
    {"name": "permission:read", "description": "Allows reading permission information."},
    {"name": "permission:update", "description": "Allows updating permission information (use with caution)."},
    {"name": "permission:delete", "description": "Allows deleting permissions (use with caution)."},
]

PERMISSIONS_HR = [
    {"name": "hr:module:access", "description": "Grants access to the HR module."},

    {"name": "department:create", "description": "Allows creating new departments."},
    {"name": "department:read", "description": "Allows reading department information."},
    {"name": "department:update", "description": "Allows updating department information."},
    {"name": "department:delete", "description": "Allows deleting departments."},

    {"name": "designation:create", "description": "Allows creating new designations."},
    {"name": "designation:read", "description": "Allows reading designation information."},
    {"name": "designation:update", "description": "Allows updating designation information."},
    {"name": "designation:delete", "description": "Allows deleting designations."},

    {"name": "employee:create", "description": "Allows creating new employee records."},
    {"name": "employee:read", "description": "Allows reading employee records."},
    {"name": "employee:update", "description": "Allows updating employee records."},
    {"name": "employee:delete", "description": "Allows deleting employee records."},

    # Future HR permissions could be added here, e.g.:
    # {"name": "salary:read", "description": "Allows reading employee salary information."},
    # {"name": "salary:update", "description": "Allows updating employee salary information."},
    # {"name": "leave_request:create", "description": "Allows creating leave requests."},
    # {"name": "leave_request:approve", "description": "Allows approving/rejecting leave requests."},
    # {"name": "attendance:record", "description": "Allows recording employee attendance."},
    # {"name": "report:hr:generate", "description": "Allows generating HR reports."},
]

ALL_PERMISSIONS = PERMISSIONS_ADMIN + PERMISSIONS_HR


# --- Roles Configuration ---
# List of dictionaries: {"name": "Role Name", "description": "Description", "permissions": ["permission:name1", "permission:name2"]}

ROLES_CONFIG = [
    {
        "name": "System Administrator",
        "description": "Has all permissions in the system.",
        "permissions": [p["name"] for p in ALL_PERMISSIONS] # Assign all defined permissions
    },
    {
        "name": "HR Manager",
        "description": "Manages all aspects of the HR module.",
        "permissions": [
            "hr:module:access",
            "department:create", "department:read", "department:update", "department:delete",
            "designation:create", "designation:read", "designation:update", "designation:delete",
            "employee:create", "employee:read", "employee:update", "employee:delete",
            # Also give HR Manager user management permissions for HR users if needed, e.g.
            # "user:create", "user:read", "user:update" (scoped to HR users if possible)
        ]
    },
    {
        "name": "HR Assistant",
        "description": "Assists with HR tasks, has limited access.",
        "permissions": [
            "hr:module:access",
            "department:read",
            "designation:read",
            "employee:create", # As per previous test setup
            "employee:read",
        ]
    },
    {
        "name": "Basic User",
        "description": "Default role for standard users with no special privileges.",
        "permissions": [
            # Example: "profile:read_self", "profile:update_self"
            # For now, no specific app permissions beyond being an authenticated user.
        ]
    }
]
