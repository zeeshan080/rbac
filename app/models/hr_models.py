import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel
from datetime import date, datetime # Added datetime for requested_at

if TYPE_CHECKING:
    from .user import User # For Employee.user and LeaveRequest.reviewed_by_user

class Department(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500, nullable=True)

    employees: List["Employee"] = Relationship(back_populates="department")

class Designation(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    title: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500, nullable=True)

    employees: List["Employee"] = Relationship(back_populates="designation")

class Employee(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field(unique=True, index=True, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20, nullable=True)
    hire_date: Optional[date] = Field(default=None, nullable=True)
    job_title: Optional[str] = Field(default=None, max_length=100, nullable=True)

    department_id: Optional[uuid.UUID] = Field(default=None, foreign_key="department.id", nullable=True, index=True)
    designation_id: Optional[uuid.UUID] = Field(default=None, foreign_key="designation.id", nullable=True, index=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", nullable=True, unique=True, index=True)

    department: Optional["Department"] = Relationship(back_populates="employees")
    designation: Optional["Designation"] = Relationship(back_populates="employees")
    user: Optional["User"] = Relationship(back_populates="employee_profile")

    leave_requests: List["LeaveRequest"] = Relationship(back_populates="employee") # Added

class LeaveRequest(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    employee_id: uuid.UUID = Field(foreign_key="employee.id", index=True, nullable=False)
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    reason: Optional[str] = Field(default=None, max_length=500, nullable=True)
    status: str = Field(default="pending", index=True, max_length=20, nullable=False) # E.g., pending, approved, rejected, cancelled

    requested_at: datetime = Field(default_factory=datetime.utcnow, nullable=False) # Use datetime.utcnow for default

    reviewed_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", nullable=True, index=True)
    review_comments: Optional[str] = Field(default=None, max_length=500, nullable=True)
    reviewed_at: Optional[datetime] = Field(default=None, nullable=True)

    employee: "Employee" = Relationship(back_populates="leave_requests")
    reviewed_by_user: Optional["User"] = Relationship(back_populates="reviewed_leave_requests")
