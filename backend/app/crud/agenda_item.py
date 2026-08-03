from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agenda_item import AgendaItem
from app.schemas.agenda_item import AgendaItemCreate, AgendaItemUpdate


def get(db: Session, *, id: int) -> AgendaItem | None:
    """Fetch an agenda item by primary key."""
    return db.get(AgendaItem, id)


def get_multi_by_event(
    db: Session, *, event_id: int
) -> Sequence[AgendaItem]:
    """List an event's agenda items, ordered by start_time then sort_order."""
    stmt = (
        select(AgendaItem)
        .where(AgendaItem.event_id == event_id)
        .order_by(AgendaItem.start_time, AgendaItem.sort_order)
    )
    return db.scalars(stmt).all()


def create(
    db: Session, *, obj_in: AgendaItemCreate, event_id: int
) -> AgendaItem:
    """Persist a new agenda item for the given event."""
    item = AgendaItem(**obj_in.model_dump(), event_id=event_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update(
    db: Session, *, db_obj: AgendaItem, obj_in: AgendaItemUpdate
) -> AgendaItem:
    """Apply a partial update to an existing agenda item."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, db_obj: AgendaItem) -> None:
    """Remove an agenda item."""
    db.delete(db_obj)
    db.commit()


def reorder(
    db: Session, *, event_id: int, item_ids: list[int]
) -> Sequence[AgendaItem]:
    """Set each item's ``sort_order`` to its position in ``item_ids``.

    Callers must validate that ``item_ids`` matches the event's items exactly.
    """
    by_id = {
        item.id: item
        for item in get_multi_by_event(db, event_id=event_id)
    }
    for position, item_id in enumerate(item_ids):
        by_id[item_id].sort_order = position
    db.commit()
    return get_multi_by_event(db, event_id=event_id)
