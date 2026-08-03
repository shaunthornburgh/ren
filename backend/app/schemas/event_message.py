from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventMessageCreate(BaseModel):
    """Payload to broadcast a message to an event's guests."""

    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class EventMessageRead(BaseModel):
    """A sent message record (history)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    body: str
    recipient_count: int
    created_at: datetime
