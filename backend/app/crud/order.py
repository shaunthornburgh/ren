from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_type import TicketType
from app.schemas.order import OrderCreate


class OrderError(Exception):
    """Base class for business-rule failures while placing an order."""


class TicketTypeNotFoundError(OrderError):
    """A requested ticket type does not exist."""


class QuantityExceedsMaxError(OrderError):
    """Requested quantity exceeds the ticket type's max_per_order."""


class InsufficientStockError(OrderError):
    """Not enough inventory remains to satisfy the request."""


def get_multi_by_user(
    db: Session,
    *,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Order]:
    """List a user's orders (newest first), with tickets eagerly loaded."""
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.tickets))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def create(db: Session, *, obj_in: OrderCreate, user_id: int) -> Order:
    """Place an order atomically.

    Locks the requested ticket types, validates availability and per-order
    limits, decrements stock, and issues one ticket per unit. The whole thing
    commits as a single transaction; any failure rolls back cleanly, leaving
    inventory untouched.
    """
    # Aggregate quantities so duplicate lines can't dodge stock/limit checks.
    wanted: dict[int, int] = defaultdict(int)
    for item in obj_in.items:
        wanted[item.ticket_type_id] += item.quantity

    try:
        # Lock the rows (ordered by id to avoid deadlocks) for the duration
        # of the transaction so concurrent orders can't oversell.
        stmt = (
            select(TicketType)
            .where(TicketType.id.in_(wanted))
            .order_by(TicketType.id)
            .with_for_update()
        )
        ticket_types = {tt.id: tt for tt in db.scalars(stmt).all()}

        order = Order(user_id=user_id, status=OrderStatus.PAID)
        total = 0

        for ticket_type_id, quantity in wanted.items():
            ticket_type = ticket_types.get(ticket_type_id)
            if ticket_type is None:
                raise TicketTypeNotFoundError(
                    f"Ticket type {ticket_type_id} not found."
                )
            if quantity > ticket_type.max_per_order:
                raise QuantityExceedsMaxError(
                    f"Cannot buy {quantity} of '{ticket_type.name}'; "
                    f"max per order is {ticket_type.max_per_order}."
                )
            if quantity > ticket_type.quantity_available:
                raise InsufficientStockError(
                    f"Only {ticket_type.quantity_available} of "
                    f"'{ticket_type.name}' remain."
                )

            ticket_type.quantity_available -= quantity
            total += ticket_type.price * quantity
            order.tickets.extend(
                Ticket(
                    ticket_type_id=ticket_type_id,
                    owner_id=user_id,
                    status=TicketStatus.VALID,
                )
                for _ in range(quantity)
            )

        order.total_amount = total
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise
