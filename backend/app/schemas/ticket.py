from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ticket import TicketStatus


class TicketRead(BaseModel):
    """Ticket representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TicketStatus
    ticket_type_id: int
    owner_id: int
    order_id: int
    created_at: datetime
    updated_at: datetime
