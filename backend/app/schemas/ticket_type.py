from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TicketTypeBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    quantity_available: int = Field(ge=0)
    max_per_order: int = Field(default=10, ge=1)


class TicketTypeCreate(TicketTypeBase):
    """Payload to create a ticket type. Event is taken from the path."""


class TicketTypeUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    quantity_available: int | None = Field(default=None, ge=0)
    max_per_order: int | None = Field(default=None, ge=1)


class TicketTypeRead(TicketTypeBase):
    """Ticket type representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime
