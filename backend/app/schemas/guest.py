from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus
from app.schemas.registration_question import RegistrationAnswerRead


class GuestTicketLine(BaseModel):
    """One ticket type + quantity within a guest's order (for this event)."""

    ticket_type_name: str
    quantity: int


class GuestRead(BaseModel):
    """A person who ordered tickets for an event (organizer view)."""

    order_id: int
    status: OrderStatus
    created_at: datetime
    email: str
    full_name: str | None = None
    total_quantity: int
    items: list[GuestTicketLine] = []
    answers: list[RegistrationAnswerRead] = []
