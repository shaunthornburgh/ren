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


class OrderItemRead(BaseModel):
    """A purchased line on an order (issued tickets follow once paid)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_type_id: int
    quantity: int
    unit_price: Decimal


class OrderRead(BaseModel):
    """Order representation returned to clients.

    ``tickets`` is empty until payment succeeds; ``items`` always reflects what
    was ordered.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total_amount: Decimal
    user_id: int
    items: list[OrderItemRead] = []
    tickets: list[TicketRead]
    created_at: datetime
    updated_at: datetime


class CheckoutSessionRead(BaseModel):
    """Stripe Checkout Session details the client redirects the buyer to."""

    checkout_url: str
    session_id: str
