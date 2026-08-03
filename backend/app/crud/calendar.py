import re
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.calendar import Calendar, CalendarFollower
from app.models.event import Event, EventStatus
from app.schemas.calendar import CalendarCreate, CalendarUpdate

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Turn a name into a URL-safe slug (lowercase, hyphen-separated)."""
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "calendar"


def _unique_slug(db: Session, base: str) -> str:
    """Return ``base`` (slugified) or ``base-2``/``base-3``… if already taken."""
    base = _slugify(base)
    candidate = base
    n = 2
    while db.scalar(select(Calendar.id).where(Calendar.slug == candidate)):
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def get(db: Session, *, id: int) -> Calendar | None:
    """Fetch a calendar by primary key."""
    return db.get(Calendar, id)


def get_by_slug(db: Session, *, slug: str) -> Calendar | None:
    """Fetch a calendar by its unique slug."""
    return db.scalar(select(Calendar).where(Calendar.slug == slug))


def get_multi_by_owner(db: Session, *, owner_id: int) -> list[Calendar]:
    """List a user's own calendars, newest first."""
    return list(
        db.scalars(
            select(Calendar)
            .where(Calendar.owner_id == owner_id)
            .order_by(Calendar.created_at.desc())
        ).all()
    )


def create(
    db: Session, *, obj_in: CalendarCreate, owner_id: int
) -> Calendar:
    """Persist a new calendar owned by the given user.

    Generates a unique slug from ``obj_in.slug`` when provided, else the name.
    """
    data = obj_in.model_dump()
    requested_slug = data.pop("slug", None) or data["name"]
    calendar = Calendar(
        **data,
        slug=_unique_slug(db, requested_slug),
        owner_id=owner_id,
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


def update(
    db: Session, *, db_obj: Calendar, obj_in: CalendarUpdate
) -> Calendar:
    """Apply a partial update to an existing calendar."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def follower_count(db: Session, *, calendar_id: int) -> int:
    """Number of users following a calendar."""
    return (
        db.scalar(
            select(func.count(CalendarFollower.id)).where(
                CalendarFollower.calendar_id == calendar_id
            )
        )
        or 0
    )


def follower_counts(db: Session, *, calendar_ids: Sequence[int]) -> dict[int, int]:
    """Map each calendar id to its follower count in one query."""
    if not calendar_ids:
        return {}
    rows = db.execute(
        select(CalendarFollower.calendar_id, func.count(CalendarFollower.id))
        .where(CalendarFollower.calendar_id.in_(calendar_ids))
        .group_by(CalendarFollower.calendar_id)
    ).all()
    return {cal_id: count for cal_id, count in rows}


def is_following(db: Session, *, calendar_id: int, user_id: int) -> bool:
    """Whether ``user_id`` currently follows ``calendar_id``."""
    return (
        db.scalar(
            select(CalendarFollower.id).where(
                CalendarFollower.calendar_id == calendar_id,
                CalendarFollower.user_id == user_id,
            )
        )
        is not None
    )


def follow(
    db: Session, *, calendar_id: int, user_id: int
) -> CalendarFollower:
    """Follow a calendar. Idempotent — returns the existing link if present."""
    existing = db.scalar(
        select(CalendarFollower).where(
            CalendarFollower.calendar_id == calendar_id,
            CalendarFollower.user_id == user_id,
        )
    )
    if existing is not None:
        return existing
    link = CalendarFollower(calendar_id=calendar_id, user_id=user_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def unfollow(db: Session, *, calendar_id: int, user_id: int) -> bool:
    """Unfollow a calendar. Returns True if a follow was removed."""
    link = db.scalar(
        select(CalendarFollower).where(
            CalendarFollower.calendar_id == calendar_id,
            CalendarFollower.user_id == user_id,
        )
    )
    if link is None:
        return False
    db.delete(link)
    db.commit()
    return True


def get_followers(
    db: Session, *, calendar_id: int
) -> Sequence[CalendarFollower]:
    """List follow links for a calendar, with the follower user loaded."""
    from sqlalchemy.orm import selectinload

    return db.scalars(
        select(CalendarFollower)
        .where(CalendarFollower.calendar_id == calendar_id)
        .options(selectinload(CalendarFollower.user))
        .order_by(CalendarFollower.created_at.desc())
    ).all()


def get_follower_ids(db: Session, *, calendar_id: int) -> list[int]:
    """User ids following a calendar (used when fanning out notifications)."""
    return list(
        db.scalars(
            select(CalendarFollower.user_id).where(
                CalendarFollower.calendar_id == calendar_id
            )
        ).all()
    )


def get_upcoming_events(
    db: Session, *, calendar_id: int, limit: int = 50
) -> Sequence[Event]:
    """Published events on a calendar that haven't ended yet, soonest first."""
    now = datetime.now(timezone.utc)
    return db.scalars(
        select(Event)
        .where(
            Event.calendar_id == calendar_id,
            Event.status == EventStatus.PUBLISHED,
            Event.end_datetime >= now,
        )
        .order_by(Event.start_datetime)
        .limit(limit)
    ).all()
