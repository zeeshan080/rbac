import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
from datetime import date # For hire_date

if TYPE_CHECKING:
    from .user import User # For Employee.user relationship

class Department(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500, nullable=True) # Explicitly nullable for Optional fields

    employees: List["Employee"] = Relationship(back_populates="department")

class Designation(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    title: str = Field(unique=True, index=True, max_length=100) # e.g., "Software Engineer", "Senior Manager"
    description: Optional[str] = Field(default=None, max_length=500, nullable=True)

    employees: List["Employee"] = Relationship(back_populates="designation")

class Employee(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field(unique=True, index=True, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20, nullable=True)
    hire_date: Optional[date] = Field(default=None, nullable=True)
    job_title: Optional[str] = Field(default=None, max_length=100, nullable=True) # Specific title, e.g. "Team Lead - Backend"

    department_id: Optional[uuid.UUID] = Field(default=None, foreign_key="department.id", nullable=True, index=True)
    designation_id: Optional[uuid.UUID] = Field(default=None, foreign_key="designation.id", nullable=True, index=True)

    # Link to the main User model (if this employee is also a system user)
    # This implies a one-to-one relationship from User to Employee profile if unique=True
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", nullable=True, unique=True, index=True)

    department: Optional["Department"] = Relationship(back_populates="employees")
    designation: Optional["Designation"] = Relationship(back_populates="employees")
    user: Optional["User"] = Relationship(back_populates="employee_profile") # Will add employee_profile to User model
