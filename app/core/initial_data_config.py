# app/core/initial_data_config.py

# --- Default Superuser Configuration ---
DEFAULT_SUPERUSER_EMAIL = "admin@example.com"
DEFAULT_SUPERUSER_USERNAME = "admin"

# --- Permissions Configuration ---
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

    # New Leave Request Permissions
    {"name": "leave_request:create_own", "description": "Allows an employee (linked user) to create their own leave requests."},
    {"name": "leave_request:create_for_others", "description": "Allows HR personnel to create leave requests for any employee."},
    {"name": "leave_request:read_own", "description": "Allows an employee (linked user) to read their own leave requests."},
    {"name": "leave_request:read_all", "description": "Allows authorized personnel (HR) to read all leave requests."},
    {"name": "leave_request:update_status", "description": "Allows authorized personnel (HR Manager) to approve, reject, or cancel leave requests."},
    {"name": "leave_request:cancel_own", "description": "Allows an employee (linked user) to cancel their own PENDING leave requests."},
]

ALL_PERMISSIONS = PERMISSIONS_ADMIN + PERMISSIONS_HR


# --- Roles Configuration ---
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
            # Leave Request permissions for HR Manager
            "leave_request:create_for_others",
            "leave_request:read_all",
            "leave_request:update_status",
            # Assuming HR Manager is also a user who might take leave
            "leave_request:create_own",
            "leave_request:read_own",
            "leave_request:cancel_own",
        ]
    },
    {
        "name": "HR Assistant",
        "description": "Assists with HR tasks, has limited access.",
        "permissions": [
            "hr:module:access",
            "department:read",
            "designation:read",
            "employee:create",
            "employee:read",
            # Leave Request permissions for HR Assistant
            "leave_request:read_all",
            # "leave_request:create_for_others", # Optional, as per script
            # Assuming HR Assistant is also a user who might take leave
            "leave_request:create_own",
            "leave_request:read_own",
            "leave_request:cancel_own",
        ]
    },
    {
        "name": "Basic User",
        "description": "Default role for standard users (e.g., employees who are system users).",
        "permissions": [
            # Permissions for employees to manage their own leave requests
            "leave_request:create_own",
            "leave_request:read_own",
            "leave_request:cancel_own",
        ]
    }
]
