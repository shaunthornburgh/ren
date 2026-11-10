from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketStatus


class TicketRead(BaseModel):
    """Ticket representation returned to its buyer (includes the check-in
    code, so never serialise this for anyone else)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    status: TicketStatus
    ticket_type_id: int
    owner_id: int
    order_id: int
    checked_in_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CheckInRequest(BaseModel):
    """A code presented at the door, scanned from a QR code or typed in.

    ``event_id`` scopes the check-in to the event being scanned for, so a
    ticket for some other event the caller also manages is rejected instead of
    silently admitted.
    """

    code: str = Field(min_length=1, max_length=64)
    event_id: int | None = None


class CheckInGuest(BaseModel):
    """Who the ticket belongs to."""

    user_id: int
    email: str
    full_name: str | None = None


class CheckInResult(BaseModel):
    """A successfully checked-in ticket, with enough context for door staff."""

    ticket_id: int
    code: str
    status: TicketStatus
    checked_in_at: datetime | None
    ticket_type_name: str
    event_id: int
    event_title: str
    guest: CheckInGuest


class CheckInStats(BaseModel):
    """Door progress for an event."""

    checked_in: int
    total: int
