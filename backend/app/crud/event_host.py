from collections.abc import Sequence

from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import Session, selectinload

from app.models.calendar import Calendar
from app.models.event import Event
from app.models.event_host import EventHost, HostRole, HostStatus
from app.models.user import User, UserRole
from app.schemas.event_host import EventHostCreate, EventHostUpdate


def get(db: Session, *, id: int) -> EventHost | None:
    """Fetch a host row by primary key."""
    return db.get(EventHost, id)


def get_multi_by_event(db: Session, *, event_id: int) -> Sequence[EventHost]:
    """List all host rows for an event (manager view), oldest first."""
    stmt = (
        select(EventHost)
        .where(EventHost.event_id == event_id)
        .order_by(EventHost.created_at)
    )
    return db.scalars(stmt).all()


def get_public_by_event(db: Session, *, event_id: int) -> Sequence[EventHost]:
    """List host rows flagged to show on the public event page."""
    stmt = (
        select(EventHost)
        .where(
            EventHost.event_id == event_id,
            EventHost.show_on_page.is_(True),
        )
        .order_by(EventHost.created_at)
    )
    return db.scalars(stmt).all()


def get_by_event_and_email(
    db: Session, *, event_id: int, email: str
) -> EventHost | None:
    """Fetch a host row by its (event, email) unique key."""
    return db.scalar(
        select(EventHost).where(
            EventHost.event_id == event_id, EventHost.email == email
        )
    )


def create(
    db: Session, *, obj_in: EventHostCreate, event_id: int
) -> EventHost:
    """Invite a host by email.

    If a user with that email already exists, the row is linked and marked
    accepted; otherwise it stays pending until that user signs up / logs in.
    """
    email = str(obj_in.email)
    existing_user = db.scalar(select(User).where(User.email == email))
    host = EventHost(
        event_id=event_id,
        email=email,
        name=obj_in.name,
        role=obj_in.role,
        show_on_page=obj_in.show_on_page,
        user_id=existing_user.id if existing_user else None,
        status=HostStatus.ACCEPTED if existing_user else HostStatus.PENDING,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


def update(
    db: Session, *, db_obj: EventHost, obj_in: EventHostUpdate
) -> EventHost:
    """Apply a partial update to a host row."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, *, db_obj: EventHost) -> None:
    """Remove a host row."""
    db.delete(db_obj)
    db.commit()


def can_manage(db: Session, *, event: Event, user: User) -> bool:
    """Whether ``user`` may manage ``event``.

    True for admins, the event's creator, the owner of the event's calendar,
    and any user linked to an accepted *manager* host row for the event.
    """
    if user.role is UserRole.ADMIN:
        return True
    if event.organizer_id == user.id:
        return True
    if event.calendar_id is not None:
        calendar_owner_id = db.scalar(
            select(Calendar.owner_id).where(Calendar.id == event.calendar_id)
        )
        if calendar_owner_id == user.id:
            return True
    host = db.scalar(
        select(EventHost.id).where(
            EventHost.event_id == event.id,
            EventHost.user_id == user.id,
            EventHost.role == HostRole.MANAGER,
            EventHost.status == HostStatus.ACCEPTED,
        )
    )
    return host is not None


def link_pending_for_user(db: Session, *, user: User) -> int:
    """Link any pending host invites matching a user's email to their account.

    Called on register/login. Sets ``user_id`` and marks the rows accepted.
    Returns the number of rows linked.
    """
    result = db.execute(
        sa_update(EventHost)
        .where(
            EventHost.email == user.email,
            EventHost.user_id.is_(None),
        )
        .values(user_id=user.id, status=HostStatus.ACCEPTED)
    )
    db.commit()
    return result.rowcount or 0
