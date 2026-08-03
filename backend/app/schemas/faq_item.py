from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FaqItemBase(BaseModel):
    question: str = Field(min_length=1, max_length=512)
    answer: str = Field(min_length=1)
    sort_order: int = 0


class FaqItemCreate(FaqItemBase):
    """Payload to create a FAQ item. Event is taken from the path."""


class FaqItemUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    question: str | None = Field(default=None, min_length=1, max_length=512)
    answer: str | None = Field(default=None, min_length=1)
    sort_order: int | None = None


class FaqItemRead(FaqItemBase):
    """FAQ item representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime


class FaqReorder(BaseModel):
    """New ordering for an event's FAQ items, by id.

    ``item_ids`` must contain exactly the event's current FAQ item ids;
    ``sort_order`` is set to each id's position in the list.
    """

    item_ids: list[int] = Field(min_length=1)
