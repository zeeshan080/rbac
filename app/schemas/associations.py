import uuid
from pydantic import BaseModel

class UserRoleLink(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID

class RolePermissionLink(BaseModel):
    role_id: uuid.UUID
    permission_id: uuid.UUID
