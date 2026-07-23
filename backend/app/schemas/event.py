from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.event import EventStatus


class EventBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    location: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=512)
    capacity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_dates(self) -> "EventBase":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be after start_datetime")
        return self


class EventCreate(EventBase):
    """Payload to create an event. Organizer is inferred from the token."""

    status: EventStatus = EventStatus.DRAFT


class EventUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=512)
    capacity: int | None = Field(default=None, ge=0)
    status: EventStatus | None = None


class EventRead(EventBase):
    """Event representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: EventStatus
    organizer_id: int
    created_at: datetime
    updated_at: datetime


class OrganizerEventRead(EventRead):
    """Event plus aggregate sales stats, for the organizer dashboard."""

    ticket_types_count: int
    tickets_sold: int
    tickets_remaining: int
    revenue: Decimal
