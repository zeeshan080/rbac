import uuid
from typing import Optional, List # List might be needed for future nested schemas
from pydantic import BaseModel, EmailStr, Field
from datetime import date

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

class DepartmentUpdate(BaseModel): # Using BaseModel for update allows all fields to be optional
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
class EmployeeBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr # Assuming email is required for an employee record
    phone_number: Optional[str] = Field(default=None, max_length=20)
    hire_date: Optional[date] = None
    job_title: Optional[str] = Field(default=None, max_length=100)

    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None # Link to a system user account

class EmployeeCreate(EmployeeBase):
    # Password is not handled here; if linking to a User, that's separate or part of User creation.
    pass

class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    # Nested schemas for related data when reading an employee
    department: Optional[DepartmentRead] = None
    designation: Optional[DesignationRead] = None
    # Consider adding a minimal User schema if user details are needed:
    # user: Optional[UserReadMinimal] = None

    class Config:
        from_attributes = True

class EmployeeUpdate(BaseModel): # All fields optional for PUT/PATCH
    first_name: Optional[str] = Field(default=None, max_length=50)
    last_name: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, max_length=20)
    hire_date: Optional[date] = None
    job_title: Optional[str] = Field(default=None, max_length=100)
    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None # Allow updating the linked user_id, with care for uniqueness
    # If user_id is changed, uniqueness constraint on Employee.user_id should be handled.
