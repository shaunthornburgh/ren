import logging
from collections.abc import Sequence

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.orm import Session

from app import crud
from app.models.event import Event
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


def notify_new_event(db: Session, *, event: Event) -> int:
    """Notify every follower of the event's calendar that it was published.

    No-op (returns 0) when the event has no calendar. The calendar owner is
    skipped — they published it. Returns the number of notifications created.
    """
    if event.calendar_id is None:
        return 0

    calendar = crud.calendar.get(db, id=event.calendar_id)
    if calendar is None:
        return 0

    follower_ids = [
        uid
        for uid in crud.calendar.get_follower_ids(db, calendar_id=calendar.id)
        if uid != calendar.owner_id
    ]
    if not follower_ids:
        logger.info(
            "Event %s published on calendar %s — no followers to notify.",
            event.id,
            calendar.id,
        )
        return 0

    title = f"New event: {event.title}"
    message = f"{calendar.name} just published a new event."
    db.add_all(
        Notification(
            user_id=uid,
            type=NotificationType.EVENT_PUBLISHED,
            title=title,
            message=message,
            event_id=event.id,
            calendar_id=calendar.id,
        )
        for uid in follower_ids
    )
    db.commit()

    logger.info(
        "Notified %d follower(s) of calendar %s about event %s.",
        len(follower_ids),
        calendar.id,
        event.id,
    )
    return len(follower_ids)


def get_multi_by_user(
    db: Session, *, user_id: int, unread_only: bool = False, limit: int = 50
) -> Sequence[Notification]:
    """List a user's notifications, newest first."""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return db.scalars(stmt).all()


def unread_count(db: Session, *, user_id: int) -> int:
    """Count a user's unread notifications."""
    return (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_all_read(db: Session, *, user_id: int) -> int:
    """Mark all of a user's notifications read. Returns rows affected."""
    result = db.execute(
        sa_update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.commit()
    return result.rowcount or 0
