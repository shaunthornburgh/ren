from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.faq_item import EventFaqItem
from app.schemas.faq_item import FaqItemCreate, FaqItemUpdate


def get(db: Session, *, id: int) -> EventFaqItem | None:
    """Fetch a FAQ item by primary key."""
    return db.get(EventFaqItem, id)


def get_multi_by_event(db: Session, *, event_id: int) -> Sequence[EventFaqItem]:
    """List an event's FAQ items, ordered by sort_order then id."""
    stmt = (
        select(EventFaqItem)
        .where(EventFaqItem.event_id == event_id)
        .order_by(EventFaqItem.sort_order, EventFaqItem.id)
    )
    return db.scalars(stmt).all()


def create(
    db: Session, *, obj_in: FaqItemCreate, event_id: int
) -> EventFaqItem:
    """Persist a new FAQ item for the given event."""
    item = EventFaqItem(**obj_in.model_dump(), event_id=event_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update(
    db: Session, *, db_obj: EventFaqItem, obj_in: FaqItemUpdate
) -> EventFaqItem:
    """Apply a partial update to an existing FAQ item."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, db_obj: EventFaqItem) -> None:
    """Remove a FAQ item."""
    db.delete(db_obj)
    db.commit()


def reorder(
    db: Session, *, event_id: int, item_ids: list[int]
) -> Sequence[EventFaqItem]:
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
