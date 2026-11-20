from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.event import Event, EventStatus
from app.models.event_host import EventHost, HostRole, HostStatus
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_type import TicketType
from app.schemas.event import (
    AnalyticsTotals,
    EventAnalytics,
    EventCreate,
    EventUpdate,
    OrderStatusCounts,
    TicketTypeAnalytics,
)

_ZERO = Decimal("0.00")


class EventStats(TypedDict):
    ticket_types_count: int
    tickets_sold: int
    tickets_remaining: int
    checked_in: int
    revenue: Decimal


class TicketTypeStats(TypedDict):
    sold: int
    checked_in: int
    revenue: Decimal


def _ticket_type_stats(
    db: Session, *, ticket_type_ids: list[int]
) -> dict[int, TicketTypeStats]:
    """Per-ticket-type sales figures, keyed by ticket type id.

    ``sold`` counts valid or used tickets, ``checked_in`` counts used ones, and
    ``revenue`` is the price actually paid (quantity x unit price on paid
    orders), so later price edits don't rewrite past revenue. Types with no
    activity are present with zeros.
    """
    stats: dict[int, TicketTypeStats] = {
        type_id: TicketTypeStats(sold=0, checked_in=0, revenue=_ZERO)
        for type_id in ticket_type_ids
    }
    if not ticket_type_ids:
        return stats

    ticket_rows = db.execute(
        select(
            Ticket.ticket_type_id,
            func.count(Ticket.id).filter(
                Ticket.status != TicketStatus.CANCELLED
            ),
            func.count(Ticket.id).filter(Ticket.status == TicketStatus.USED),
        )
        .where(Ticket.ticket_type_id.in_(ticket_type_ids))
        .group_by(Ticket.ticket_type_id)
    ).all()
    for type_id, sold, checked_in in ticket_rows:
        stats[type_id]["sold"] = sold
        stats[type_id]["checked_in"] = checked_in

    revenue_rows = db.execute(
        select(
            OrderItem.ticket_type_id,
            func.sum(OrderItem.quantity * OrderItem.unit_price),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.ticket_type_id.in_(ticket_type_ids),
            Order.status == OrderStatus.PAID,
        )
        .group_by(OrderItem.ticket_type_id)
    ).all()
    for type_id, revenue in revenue_rows:
        stats[type_id]["revenue"] = Decimal(revenue or 0)

    return stats


def get(db: Session, *, id: int) -> Event | None:
    """Fetch an event by primary key."""
    return db.get(Event, id)


def get_multi(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    status: EventStatus | None = None,
    organizer_id: int | None = None,
) -> Sequence[Event]:
    """List events, optionally filtered by status and/or organizer."""
    stmt = select(Event)
    if status is not None:
        stmt = stmt.where(Event.status == status)
    if organizer_id is not None:
        stmt = stmt.where(Event.organizer_id == organizer_id)
    stmt = stmt.order_by(Event.start_datetime).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def get_multi_for_admin(
    db: Session,
    *,
    q: str | None = None,
    status: EventStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Sequence[Event]:
    """List every event (any status), latest start first, for the admin area.

    Eager-loads the organizer so callers can resolve display names cheaply.
    """
    stmt = select(Event).options(selectinload(Event.organizer))
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))
    if status is not None:
        stmt = stmt.where(Event.status == status)
    stmt = (
        stmt.order_by(Event.start_datetime.desc(), Event.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def get_multi_by_organizer_with_stats(
    db: Session, *, organizer_id: int
) -> list[tuple[Event, EventStats]]:
    """List an organizer's events (newest first) with aggregate sales stats.

    ``tickets_sold``, ``checked_in`` and ``revenue`` follow
    ``_ticket_type_stats``. ``tickets_remaining`` is the inventory still
    available across the event's ticket types.
    """
    events = db.scalars(
        select(Event)
        .where(Event.organizer_id == organizer_id)
        .options(selectinload(Event.ticket_types))
        .order_by(Event.start_datetime.desc())
    ).all()

    type_ids = [tt.id for e in events for tt in e.ticket_types]
    by_type = _ticket_type_stats(db, ticket_type_ids=type_ids)

    results: list[tuple[Event, EventStats]] = []
    for event in events:
        type_stats = [by_type[tt.id] for tt in event.ticket_types]
        results.append(
            (
                event,
                EventStats(
                    ticket_types_count=len(event.ticket_types),
                    tickets_sold=sum(t["sold"] for t in type_stats),
                    tickets_remaining=sum(
                        tt.quantity_available for tt in event.ticket_types
                    ),
                    checked_in=sum(t["checked_in"] for t in type_stats),
                    revenue=sum((t["revenue"] for t in type_stats), _ZERO),
                ),
            )
        )
    return results


def get_analytics(db: Session, *, event: Event) -> EventAnalytics:
    """Sales, revenue, attendance and order counts for one event."""
    ticket_types = db.scalars(
        select(TicketType)
        .where(TicketType.event_id == event.id)
        .order_by(TicketType.id)
    ).all()
    type_ids = [tt.id for tt in ticket_types]
    by_type = _ticket_type_stats(db, ticket_type_ids=type_ids)

    rows = [
        TicketTypeAnalytics(
            ticket_type_id=tt.id,
            name=tt.name,
            price=tt.price,
            sold=by_type[tt.id]["sold"],
            remaining=tt.quantity_available,
            checked_in=by_type[tt.id]["checked_in"],
            revenue=by_type[tt.id]["revenue"],
        )
        for tt in ticket_types
    ]
    totals = AnalyticsTotals(
        sold=sum(r.sold for r in rows),
        remaining=sum(r.remaining for r in rows),
        checked_in=sum(r.checked_in for r in rows),
        revenue=sum((r.revenue for r in rows), _ZERO),
    )

    # Distinct orders per status that include any of this event's ticket types.
    orders = {s: 0 for s in OrderStatus}
    if type_ids:
        order_rows = db.execute(
            select(Order.status, func.count(distinct(Order.id)))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(OrderItem.ticket_type_id.in_(type_ids))
            .group_by(Order.status)
        ).all()
        for order_status, count in order_rows:
            orders[order_status] = count

    return EventAnalytics(
        ticket_types=rows,
        totals=totals,
        attendance_rate=(
            round(totals.checked_in / totals.sold, 4) if totals.sold else None
        ),
        orders=OrderStatusCounts(
            paid=orders[OrderStatus.PAID],
            pending=orders[OrderStatus.PENDING],
            cancelled=orders[OrderStatus.CANCELLED],
        ),
    )


def get_upcoming_hosted_by_user(
    db: Session, *, user_id: int, limit: int = 50
) -> Sequence[Event]:
    """Upcoming published events a user hosts, for their public profile.

    Includes events they created, and events where they're an accepted host
    that is either shown on the page or a manager. Soonest first, de-duplicated.
    """
    now = datetime.now(timezone.utc)
    host_event_ids = (
        select(EventHost.event_id)
        .where(
            EventHost.user_id == user_id,
            EventHost.status == HostStatus.ACCEPTED,
            or_(
                EventHost.show_on_page.is_(True),
                EventHost.role == HostRole.MANAGER,
            ),
        )
        .scalar_subquery()
    )
    stmt = (
        select(Event)
        .where(
            Event.status == EventStatus.PUBLISHED,
            Event.end_datetime >= now,
            or_(
                Event.organizer_id == user_id,
                Event.id.in_(host_event_ids),
            ),
        )
        .order_by(Event.start_datetime)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def create(db: Session, *, obj_in: EventCreate, organizer_id: int) -> Event:
    """Persist a new event owned by the given organizer."""
    event = Event(
        **obj_in.model_dump(),
        organizer_id=organizer_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update(db: Session, *, db_obj: Event, obj_in: EventUpdate) -> Event:
    """Apply a partial update to an existing event."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
