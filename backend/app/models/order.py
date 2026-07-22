import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order_item import OrderItem
    from app.models.ticket import Ticket
    from app.models.user import User


class OrderStatus(str, enum.Enum):
    """Lifecycle of an order.

    An order is created as PENDING with its inventory reserved, then moves to
    PAID once Stripe confirms payment (at which point tickets are issued). If
    payment never completes (the Checkout Session expires or fails) it becomes
    CANCELLED and the reserved inventory is released.
    """

    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Order(Base):
    """A purchase made by a user, grouping one or more issued tickets."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )

    # Stripe correlation. Set when a Checkout Session is created for the order;
    # the payment intent is recorded once payment succeeds. Indexed so the
    # webhook can look an order up by its session id if needed.
    stripe_session_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user: Mapped["User"] = relationship(back_populates="orders")

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="order",
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
