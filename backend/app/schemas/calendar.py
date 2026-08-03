from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.event import EventRead


class CalendarBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=512)
    is_public: bool = True


class CalendarCreate(CalendarBase):
    """Payload to create a calendar. Owner is inferred from the token.

    ``slug`` is optional — when omitted it is derived from the name and made
    unique server-side.
    """

    slug: str | None = Field(default=None, min_length=1, max_length=255)


class CalendarUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=512)
    is_public: bool | None = None


class CalendarRead(CalendarBase):
    """Calendar representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    owner_id: int
    follower_count: int = 0
    created_at: datetime
    updated_at: datetime


class CalendarWithEvents(CalendarRead):
    """Public calendar page payload: the calendar plus its upcoming events.

    ``is_following`` reflects the current caller (false when unauthenticated).
    """

    upcoming_events: list[EventRead] = []
    is_following: bool = False


class FollowerRead(BaseModel):
    """A follower of a calendar (owner-only view)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    full_name: str | None = None
    followed_at: datetime
