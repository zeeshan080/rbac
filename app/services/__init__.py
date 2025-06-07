from .user_service import UserService
from .role_service import RoleService
from .permission_service import PermissionService
from .department_service import DepartmentService
from .designation_service import DesignationService
from .employee_service import EmployeeService # Added

# Optional: Instantiate services here for global availability if preferred,
# or inject them directly in routers using Depends(ServiceClass).
# user_service = UserService()
# role_service = RoleService()
# permission_service = PermissionService()
# department_service = DepartmentService()
# designation_service = DesignationService()
# employee_service = EmployeeService() # Added
