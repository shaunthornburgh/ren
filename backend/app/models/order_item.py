from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.ticket_type import TicketType


class OrderItem(Base):
    """A line on an order: how many of a ticket type were purchased.

    Recorded when an order is placed (and inventory reserved) so that the
    tickets can be issued later, once payment succeeds via the Stripe webhook.
    ``unit_price`` snapshots the price at purchase time, insulating the order
    from later price changes on the ticket type.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order: Mapped["Order"] = relationship(back_populates="items")

    ticket_type_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ticket_type: Mapped["TicketType"] = relationship()
