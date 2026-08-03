from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.event_host import HostRole, HostStatus


class EventHostCreate(BaseModel):
    """Payload to invite a host by email. Event is taken from the path."""

    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    role: HostRole = HostRole.HOST
    show_on_page: bool = True


class EventHostUpdate(BaseModel):
    """Partial update. Email is immutable (it's the invite key)."""

    name: str | None = Field(default=None, max_length=255)
    role: HostRole | None = None
    show_on_page: bool | None = None


class EventHostRead(BaseModel):
    """Full host row for the manager view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    user_id: int | None = None
    email: str
    name: str | None = None
    role: HostRole
    show_on_page: bool
    status: HostStatus
    is_creator: bool = False
    created_at: datetime
    updated_at: datetime


class PublicHostRead(BaseModel):
    """Host as shown on the public event page.

    ``user_id`` is present once the host is linked to an account, so the UI can
    link the chip to that user's public profile.
    """

    user_id: int | None = None
    name: str | None = None
    email: str
    role: HostRole
