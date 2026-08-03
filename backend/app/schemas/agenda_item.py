from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgendaItemBase(BaseModel):
    start_time: datetime
    end_time: datetime | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    speaker_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    sort_order: int = 0

    @model_validator(mode="after")
    def _check_times(self) -> "AgendaItemBase":
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time must not be before start_time")
        return self


class AgendaItemCreate(AgendaItemBase):
    """Payload to create an agenda item. Event is taken from the path."""


class AgendaItemUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    speaker_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None


class AgendaItemRead(AgendaItemBase):
    """Agenda item representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime


class AgendaReorder(BaseModel):
    """New ordering for an event's agenda items, by id.

    ``item_ids`` must contain exactly the event's current agenda item ids;
    ``sort_order`` is set to each id's position in the list.
    """

    item_ids: list[int] = Field(min_length=1)
