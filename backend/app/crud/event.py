from collections.abc import Sequence
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.event import Event, EventStatus
from app.models.ticket import Ticket, TicketStatus
from app.schemas.event import EventCreate, EventUpdate


class EventStats(TypedDict):
    ticket_types_count: int
    tickets_sold: int
    tickets_remaining: int
    revenue: Decimal


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


def get_multi_by_organizer_with_stats(
    db: Session, *, organizer_id: int
) -> list[tuple[Event, EventStats]]:
    """List an organizer's events (newest first) with aggregate sales stats.

    ``tickets_sold`` / ``revenue`` count issued (non-cancelled) tickets — which
    only exist once an order is paid. ``tickets_remaining`` is the inventory
    still available across the event's ticket types.
    """
    events = db.scalars(
        select(Event)
        .where(Event.organizer_id == organizer_id)
        .options(selectinload(Event.ticket_types))
        .order_by(Event.start_datetime.desc())
    ).all()

    type_ids = [tt.id for e in events for tt in e.ticket_types]
    sold_by_type: dict[int, int] = {}
    if type_ids:
        rows = db.execute(
            select(Ticket.ticket_type_id, func.count(Ticket.id))
            .where(
                Ticket.ticket_type_id.in_(type_ids),
                Ticket.status != TicketStatus.CANCELLED,
            )
            .group_by(Ticket.ticket_type_id)
        ).all()
        sold_by_type = {type_id: count for type_id, count in rows}

    results: list[tuple[Event, EventStats]] = []
    for event in events:
        sold = sum(sold_by_type.get(tt.id, 0) for tt in event.ticket_types)
        remaining = sum(tt.quantity_available for tt in event.ticket_types)
        revenue = sum(
            (sold_by_type.get(tt.id, 0) * tt.price for tt in event.ticket_types),
            Decimal(0),
        )
        results.append(
            (
                event,
                EventStats(
                    ticket_types_count=len(event.ticket_types),
                    tickets_sold=sold,
                    tickets_remaining=remaining,
                    revenue=revenue,
                ),
            )
        )
    return results


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
