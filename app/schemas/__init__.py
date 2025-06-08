from .user import UserBase, UserCreate, UserRead, UserUpdate, UserReadMinimal # Added UserReadMinimal
from .role import RoleBase, RoleCreate, RoleRead, RoleUpdate
from .permission import PermissionBase, PermissionCreate, PermissionRead, PermissionUpdate
from .associations import UserRoleLink, RolePermissionLink
from .common import Page
from .auth import PasswordResetRequestSchema, NewPasswordSchema
from .token import Token, TokenPayload

# Schemas for HR Module
from .hr_schemas import DepartmentBase, DepartmentCreate, DepartmentRead, DepartmentUpdate
from .hr_schemas import DesignationBase, DesignationCreate, DesignationRead, DesignationUpdate
from .hr_schemas import EmployeeBase, EmployeeCreate, EmployeeRead, EmployeeUpdate, EmployeeReadMinimal # Added EmployeeReadMinimal
from .hr_schemas import LeaveRequestBase, LeaveRequestCreate, LeaveRequestRead, LeaveRequestStatusUpdate # Added LeaveRequest schemas
