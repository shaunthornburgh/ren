from datetime import datetime
from decimal import Decimal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from app.models.event import EventStatus

_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


def _is_http_url(value: str) -> bool:
    try:
        _URL_ADAPTER.validate_python(value)
    except ValidationError:
        return False
    return True


def validate_location(
    *,
    is_online: bool,
    location: str | None,
    lat: float | None,
    lng: float | None,
) -> tuple[str, float | None, float | None]:
    """Check a location triple and return it normalised.

    Online events are addressed by a URL and carry no coordinates (any that
    were sent are dropped, so toggling in person → online cleans up after
    itself). In-person events need both a place and the coordinates Google
    returned for it, so the public page can render a map marker.

    Raises ``ValueError`` — callers surface it as a 422.
    """
    location = (location or "").strip()

    if is_online:
        if not location:
            raise ValueError("An online event needs a joining URL.")
        if not _is_http_url(location):
            raise ValueError(
                "location must be a valid http(s) URL for an online event."
            )
        return location, None, None

    if not location:
        raise ValueError("An in-person event needs a location.")
    if lat is None or lng is None:
        raise ValueError(
            "Select the location from the suggestions so we can place it on "
            "the map."
        )
    return location, lat, lng


class EventBase(BaseModel):
    """Fields shared by reads and writes.

    Deliberately permissive about location: ``EventRead`` inherits from this
    and must be able to represent rows written before the online/in-person
    split existed. The strict rules live on the write paths.
    """

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    location: str | None = Field(default=None, max_length=512)
    is_online: bool = False
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    image_url: str | None = Field(default=None, max_length=512)
    capacity: int | None = Field(default=None, ge=0)
    calendar_id: int

    @model_validator(mode="after")
    def _check_dates(self) -> "EventBase":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be after start_datetime")
        return self


class EventCreate(EventBase):
    """Payload to create an event. Organizer is inferred from the token."""

    status: EventStatus = EventStatus.DRAFT

    @model_validator(mode="after")
    def _check_location(self) -> "EventCreate":
        self.location, self.lat, self.lng = validate_location(
            is_online=self.is_online,
            location=self.location,
            lat=self.lat,
            lng=self.lng,
        )
        return self


class EventUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change.

    Location can't be validated here — the rules span ``is_online``,
    ``location`` and the coordinates, and a partial payload may set only one
    of them. The endpoint merges the payload over the stored event and
    validates the result.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = Field(default=None, max_length=512)
    is_online: bool | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    image_url: str | None = Field(default=None, max_length=512)
    capacity: int | None = Field(default=None, ge=0)
    calendar_id: int | None = None
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
