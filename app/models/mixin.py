# app/models/mixin.py
from typing import TypeVar, Optional
import uuid
from datetime import datetime, timezone
from sqlmodel import Field
from datetime import timedelta

ID = TypeVar('ID', int, uuid.UUID, str)

def now_with_system_timezone():
    # Get current time with system's local timezone
    return datetime.now().replace(microsecond=0)
# Model Mixins
class TimestampAuditMixin:
    """Base mixin for adding timestamp and audit fields to models."""

    created_at: datetime = Field(default_factory=now_with_system_timezone, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)
    created_by: Optional[uuid.UUID] = Field(default=None, nullable=True)
    updated_by: Optional[uuid.UUID] = Field(default=None, nullable=True)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True)
    deleted_by: Optional[uuid.UUID] = Field(default=None, nullable=True)
    
    def is_deleted(self) -> bool:
        """Check if the record is soft-deleted."""
        return self.deleted_at is not None

class IntPKMixin:
    """Mixin for models using integer primary keys."""
    id: Optional[int] = Field(default=None, primary_key=True)

class UUIDMixin:
    """Mixin for models using UUID primary keys."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
