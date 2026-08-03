from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.registration_question import (
    RegistrationAnswer,
    RegistrationQuestion,
)
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.order import OrderCreate


class OrderError(Exception):
    """Base class for business-rule failures while placing an order."""


class TicketTypeNotFoundError(OrderError):
    """A requested ticket type does not exist."""


class QuantityExceedsMaxError(OrderError):
    """Requested quantity exceeds the ticket type's max_per_order."""


class InsufficientStockError(OrderError):
    """Not enough inventory remains to satisfy the request."""


class MissingRequiredAnswerError(OrderError):
    """A required registration question was left unanswered."""


class InvalidQuestionError(OrderError):
    """An answer references a question that doesn't belong to this order."""


def get(db: Session, *, id: int) -> Order | None:
    """Fetch a single order with its items (and their ticket types) loaded."""
    stmt = (
        select(Order)
        .where(Order.id == id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.ticket_type),
            selectinload(Order.tickets),
        )
    )
    return db.scalars(stmt).first()


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
        .options(selectinload(Order.items), selectinload(Order.tickets))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def get_event_guests(db: Session, *, event_id: int) -> Sequence[Order]:
    """List orders containing tickets for an event (organizer's guest list).

    Newest first, with the buyer and the order's items (and their ticket types)
    eagerly loaded. An order is included if any of its items is for a ticket
    type belonging to this event.
    """
    stmt = (
        select(Order)
        .join(Order.items)
        .join(OrderItem.ticket_type)
        .where(TicketType.event_id == event_id)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.ticket_type),
            selectinload(Order.registration_answers).selectinload(
                RegistrationAnswer.question
            ),
        )
        .order_by(Order.created_at.desc())
        .distinct()
    )
    return db.scalars(stmt).unique().all()


def get_event_recipient_emails(
    db: Session,
    *,
    event_id: int,
    statuses: Sequence[OrderStatus] = (OrderStatus.PAID,),
) -> list[str]:
    """Unique emails of guests with an order (in ``statuses``) for an event."""
    stmt = (
        select(User.email)
        .join(Order, Order.user_id == User.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(TicketType, TicketType.id == OrderItem.ticket_type_id)
        .where(
            TicketType.event_id == event_id,
            Order.status.in_(statuses),
            User.is_active.is_(True),
        )
        .distinct()
    )
    return list(db.scalars(stmt).all())


def create(db: Session, *, obj_in: OrderCreate, user_id: int) -> Order:
    """Place a PENDING order, reserving inventory.

    Locks the requested ticket types, validates availability and per-order
    limits, decrements stock to reserve it, and records the purchased lines as
    OrderItems. No tickets are issued yet — that happens once Stripe confirms
    payment (see :func:`fulfill`). The whole thing commits as a single
    transaction; any failure rolls back cleanly, leaving inventory untouched.
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

        order = Order(user_id=user_id, status=OrderStatus.PENDING)
        total = 0

        for ticket_type_id, quantity in sorted(wanted.items()):
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

            ticket_type.quantity_available -= quantity  # reserve
            total += ticket_type.price * quantity
            order.items.append(
                OrderItem(
                    ticket_type_id=ticket_type_id,
                    quantity=quantity,
                    unit_price=ticket_type.price,
                )
            )

        order.total_amount = total

        _attach_registration_answers(
            db,
            order=order,
            event_ids={tt.event_id for tt in ticket_types.values()},
            answers=obj_in.answers,
        )

        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def _attach_registration_answers(
    db: Session,
    *,
    order: Order,
    event_ids: set[int],
    answers,
) -> None:
    """Validate and attach registration answers to a new order.

    Ensures every required question for the order's event(s) is answered and
    that submitted answers reference questions belonging to those events.
    """
    questions = {
        q.id: q
        for q in db.scalars(
            select(RegistrationQuestion).where(
                RegistrationQuestion.event_id.in_(event_ids)
            )
        ).all()
    }
    provided = {a.question_id: a.value.strip() for a in answers}

    for question_id in provided:
        if question_id not in questions:
            raise InvalidQuestionError(
                f"Question {question_id} does not belong to this event."
            )

    for question in questions.values():
        answer = provided.get(question.id, "")
        if question.required and not answer:
            raise MissingRequiredAnswerError(
                f"'{question.label}' is required."
            )
        if answer:
            order.registration_answers.append(
                RegistrationAnswer(question_id=question.id, value=answer)
            )


def fulfill(
    db: Session, *, order_id: int, payment_intent_id: str | None = None
) -> Order | None:
    """Mark a pending order PAID and issue its tickets.

    Idempotent and safe against concurrent webhook deliveries: the order row is
    locked for the transaction, and an order that is already PAID (or was
    CANCELLED) is returned unchanged without issuing duplicate tickets.
    """
    try:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )
        order = db.scalars(stmt).first()
        if order is None:
            return None
        if order.status is not OrderStatus.PENDING:
            # Already fulfilled or cancelled — nothing to do (idempotent).
            return order

        for item in order.items:
            order.tickets.extend(
                Ticket(
                    ticket_type_id=item.ticket_type_id,
                    owner_id=order.user_id,
                    status=TicketStatus.VALID,
                )
                for _ in range(item.quantity)
            )

        order.status = OrderStatus.PAID
        if payment_intent_id:
            order.stripe_payment_intent_id = payment_intent_id
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def release(db: Session, *, order_id: int) -> Order | None:
    """Cancel a pending order and return its reserved inventory to stock.

    Used when a Checkout Session expires or payment fails. Idempotent: only
    PENDING orders are touched, so a paid or already-cancelled order is left
    alone.
    """
    try:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )
        order = db.scalars(stmt).first()
        if order is None:
            return None
        if order.status is not OrderStatus.PENDING:
            return order

        wanted = {item.ticket_type_id for item in order.items}
        if wanted:
            tt_stmt = (
                select(TicketType)
                .where(TicketType.id.in_(wanted))
                .order_by(TicketType.id)
                .with_for_update()
            )
            ticket_types = {tt.id: tt for tt in db.scalars(tt_stmt).all()}
            for item in order.items:
                ticket_type = ticket_types.get(item.ticket_type_id)
                if ticket_type is not None:
                    ticket_type.quantity_available += item.quantity

        order.status = OrderStatus.CANCELLED
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise
