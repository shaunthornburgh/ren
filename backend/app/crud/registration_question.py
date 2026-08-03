from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registration_question import RegistrationQuestion
from app.schemas.registration_question import (
    RegistrationQuestionCreate,
    RegistrationQuestionUpdate,
)


def get(db: Session, *, id: int) -> RegistrationQuestion | None:
    """Fetch a registration question by primary key."""
    return db.get(RegistrationQuestion, id)


def get_multi_by_event(
    db: Session, *, event_id: int
) -> Sequence[RegistrationQuestion]:
    """List an event's questions, ordered by sort_order then id."""
    stmt = (
        select(RegistrationQuestion)
        .where(RegistrationQuestion.event_id == event_id)
        .order_by(RegistrationQuestion.sort_order, RegistrationQuestion.id)
    )
    return db.scalars(stmt).all()


def get_multi_by_events(
    db: Session, *, event_ids: Sequence[int]
) -> Sequence[RegistrationQuestion]:
    """List questions across several events (used when placing an order)."""
    if not event_ids:
        return []
    stmt = select(RegistrationQuestion).where(
        RegistrationQuestion.event_id.in_(event_ids)
    )
    return db.scalars(stmt).all()


def create(
    db: Session, *, obj_in: RegistrationQuestionCreate, event_id: int
) -> RegistrationQuestion:
    """Persist a new question for the given event."""
    question = RegistrationQuestion(**obj_in.model_dump(), event_id=event_id)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def update(
    db: Session,
    *,
    db_obj: RegistrationQuestion,
    obj_in: RegistrationQuestionUpdate,
) -> RegistrationQuestion:
    """Apply a partial update to an existing question."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, db_obj: RegistrationQuestion) -> None:
    """Remove a question (and, by cascade, its answers)."""
    db.delete(db_obj)
    db.commit()


def reorder(
    db: Session, *, event_id: int, item_ids: list[int]
) -> Sequence[RegistrationQuestion]:
    """Set each question's ``sort_order`` to its position in ``item_ids``.

    Callers must validate that ``item_ids`` matches the event's questions.
    """
    by_id = {
        q.id: q for q in get_multi_by_event(db, event_id=event_id)
    }
    for position, item_id in enumerate(item_ids):
        by_id[item_id].sort_order = position
    db.commit()
    return get_multi_by_event(db, event_id=event_id)
