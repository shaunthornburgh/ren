from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_message import EventMessage
from app.schemas.event_message import EventMessageCreate


def create(
    db: Session,
    *,
    obj_in: EventMessageCreate,
    event_id: int,
    sent_by_id: int,
    recipient_count: int,
) -> EventMessage:
    """Record a broadcast message sent to an event's guests."""
    message = EventMessage(
        event_id=event_id,
        sent_by_id=sent_by_id,
        subject=obj_in.subject,
        body=obj_in.body,
        recipient_count=recipient_count,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_multi_by_event(
    db: Session, *, event_id: int
) -> Sequence[EventMessage]:
    """List an event's sent messages, newest first."""
    stmt = (
        select(EventMessage)
        .where(EventMessage.event_id == event_id)
        .order_by(EventMessage.created_at.desc())
    )
    return db.scalars(stmt).all()
