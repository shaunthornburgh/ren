from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus
from app.schemas.event import EventCreate, EventUpdate


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
