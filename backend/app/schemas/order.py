from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.schemas.ticket import TicketRead


class OrderItemCreate(BaseModel):
    """A single line in a purchase: how many of a given ticket type to buy."""

    ticket_type_id: int
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    """Payload to create an order. Buyer is inferred from the token."""

    items: list[OrderItemCreate] = Field(min_length=1)


class OrderRead(BaseModel):
    """Order representation returned to clients, including issued tickets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total_amount: Decimal
    user_id: int
    tickets: list[TicketRead]
    created_at: datetime
    updated_at: datetime
