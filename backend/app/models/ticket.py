import enum
import re
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.ticket_type import TicketType
    from app.models.user import User


class TicketStatus(str, enum.Enum):
    """Lifecycle of an individual ticket."""

    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"


# Crockford base32: no I, L, O or U, so codes survive being read aloud or
# typed by hand at the door. 12 chars = 60 bits of randomness.
TICKET_CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TICKET_CODE_LENGTH = 12


def generate_ticket_code() -> str:
    """A random, unguessable ticket code (e.g. ``7K3QX9MZ2B4H``)."""
    return "".join(
        secrets.choice(TICKET_CODE_ALPHABET) for _ in range(TICKET_CODE_LENGTH)
    )


def normalize_ticket_code(raw: str) -> str:
    """Canonicalise user-entered code: uppercase, drop separators, and map the
    look-alike letters Crockford excludes (O→0, I/L→1)."""
    code = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    return code.translate(str.maketrans("OIL", "011"))


class Ticket(Base):
    """A single ticket owned by a user, issued as part of an order."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.VALID,
        nullable=False,
    )
    # Printed on / encoded in the ticket's QR code and presented at check-in.
    code: Mapped[str] = mapped_column(
        String(TICKET_CODE_LENGTH),
        unique=True,
        index=True,
        nullable=False,
        default=generate_ticket_code,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
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

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order: Mapped["Order"] = relationship(back_populates="tickets")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
