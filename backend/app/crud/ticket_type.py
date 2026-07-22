from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket_type import TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate


def get(db: Session, *, id: int) -> TicketType | None:
    """Fetch a ticket type by primary key."""
    return db.get(TicketType, id)


def get_multi_by_event(
    db: Session,
    *,
    event_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[TicketType]:
    """List ticket types belonging to a single event."""
    stmt = (
        select(TicketType)
        .where(TicketType.event_id == event_id)
        .order_by(TicketType.price)
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def create(
    db: Session, *, obj_in: TicketTypeCreate, event_id: int
) -> TicketType:
    """Persist a new ticket type for the given event."""
    ticket_type = TicketType(
        **obj_in.model_dump(),
        event_id=event_id,
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)
    return ticket_type


def update(
    db: Session, *, db_obj: TicketType, obj_in: TicketTypeUpdate
) -> TicketType:
    """Apply a partial update to an existing ticket type."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
