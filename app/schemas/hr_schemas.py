import uuid
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime # Ensure datetime is imported

# Import UserReadMinimal for use in LeaveRequestRead
from app.schemas.user import UserReadMinimal

# --- Department Schemas ---
class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentRead(DepartmentBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

# --- Designation Schemas ---
class DesignationBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

class DesignationCreate(DesignationBase):
    pass

class DesignationRead(DesignationBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class DesignationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

# --- Employee Schemas ---
class EmployeeReadMinimal(BaseModel): # For embedding in LeaveRequestRead
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr # Make sure EmailStr is available if used here
    class Config:
        from_attributes = True

class EmployeeBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=20)
    hire_date: Optional[date] = None
    job_title: Optional[str] = Field(default=None, max_length=100)
    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    department: Optional[DepartmentRead] = None
    designation: Optional[DesignationRead] = None
    # user: Optional[UserReadMinimal] = None # Can be added if needed, ensure UserReadMinimal is defined/imported
    class Config:
        from_attributes = True

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=50)
    last_name: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, max_length=20)
    hire_date: Optional[date] = None
    job_title: Optional[str] = Field(default=None, max_length=100)
    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

# --- LeaveRequest Schemas ---
class LeaveRequestBase(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=500)

class LeaveRequestCreate(LeaveRequestBase):
    # employee_id is specified when HR creates for another employee.
    # If an employee creates for themselves, employee_id is derived from their current_user context.
    employee_id: Optional[uuid.UUID] = None # Made optional, logic in router/service to determine it

class LeaveRequestRead(LeaveRequestBase):
    id: uuid.UUID
    employee_id: uuid.UUID # Always present in the read model
    status: str
    requested_at: datetime

    employee: EmployeeReadMinimal # Nested minimal employee info

    reviewed_by_user_id: Optional[uuid.UUID] = None
    review_comments: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by_user: Optional[UserReadMinimal] = None # Nested minimal reviewer info

    class Config:
        from_attributes = True

class LeaveRequestStatusUpdate(BaseModel): # For HR/Manager to approve/reject
    status: str # Should validate against allowed statuses e.g. "approved", "rejected", "cancelled"
    review_comments: Optional[str] = Field(default=None, max_length=500)
