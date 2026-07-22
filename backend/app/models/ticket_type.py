from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.ticket import Ticket


class TicketType(Base):
    """A purchasable tier for an event (e.g. "General Admission", "VIP")."""

    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_order: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event: Mapped["Event"] = relationship(back_populates="ticket_types")

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="ticket_type",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
