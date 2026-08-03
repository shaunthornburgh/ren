import logging
from collections.abc import Sequence

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.orm import Session

from app import crud
from app.core.email import NewEventEmail
from app.models.event import Event
from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)


def notify_new_event(db: Session, *, event: Event) -> NewEventEmail | None:
    """Notify every follower of the event's calendar that it was published.

    Creates one in-app :class:`Notification` per follower (skipping the
    calendar owner, who published it) and returns a :class:`NewEventEmail`
    batch the caller can hand to a background task for email delivery — or
    ``None`` when there's nothing/no-one to notify.
    """
    if event.calendar_id is None:
        return None

    calendar = crud.calendar.get(db, id=event.calendar_id)
    if calendar is None:
        return None

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
        return None

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

    emails = list(
        db.scalars(
            select(User.email).where(
                User.id.in_(follower_ids), User.is_active.is_(True)
            )
        ).all()
    )
    return NewEventEmail(
        event_id=event.id,
        event_title=event.title,
        event_start=event.start_datetime,
        calendar_name=calendar.name,
        recipient_emails=emails,
    )


def get_multi_by_user(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> Sequence[Notification]:
    """List a user's notifications, newest first."""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = (
        stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    )
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


def mark_read(
    db: Session, *, user_id: int, notification_id: int
) -> Notification | None:
    """Mark a single notification read. Scoped to its owner for safety.

    Returns the notification, or ``None`` if it doesn't exist or isn't the
    user's.
    """
    notif = db.get(Notification, notification_id)
    if notif is None or notif.user_id != user_id:
        return None
    if not notif.is_read:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif


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
