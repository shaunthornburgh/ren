import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ticket_type import TicketType
    from app.models.user import User


class TicketStatus(str, enum.Enum):
    """Lifecycle of an individual ticket."""

    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"


class Ticket(Base):
    """A single ticket owned by a user.

    An `Order` model does not exist yet; for the basic purchase flow a ticket
    is linked directly to its owner. An `order_id` FK can be added later
    without breaking this relationship.
    """

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.VALID,
        nullable=False,
    )

    ticket_type_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ticket_type: Mapped["TicketType"] = relationship(back_populates="tickets")

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner: Mapped["User"] = relationship(back_populates="tickets")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
