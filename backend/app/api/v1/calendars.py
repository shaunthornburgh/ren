from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import (
    get_current_active_user,
    get_current_user_optional,
    get_db,
    require_role,
)
from app.models.calendar import Calendar
from app.models.user import User, UserRole
from app.schemas.calendar import (
    CalendarCreate,
    CalendarRead,
    CalendarUpdate,
    CalendarWithEvents,
    FollowerRead,
)
from app.schemas.event import EventRead

router = APIRouter(prefix="/calendars", tags=["calendars"])


def _to_read(calendar: Calendar, *, follower_count: int) -> CalendarRead:
    """Build a CalendarRead, injecting the (non-column) follower count."""
    read = CalendarRead.model_validate(calendar)
    read.follower_count = follower_count
    return read


def _get_owned_calendar(
    calendar_id: int, db: Session, current_user: User
) -> Calendar:
    """Load a calendar and assert the caller owns it (admins bypass)."""
    calendar = crud.calendar.get(db, id=calendar_id)
    if calendar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found."
        )
    if (
        calendar.owner_id != current_user.id
        and current_user.role is not UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this calendar.",
        )
    return calendar


@router.post(
    "",
    response_model=CalendarRead,
    status_code=status.HTTP_201_CREATED,
)
def create_calendar(
    calendar_in: CalendarCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> CalendarRead:
    """Create a new calendar. Organizers (and admins) only."""
    calendar = crud.calendar.create(
        db, obj_in=calendar_in, owner_id=current_user.id
    )
    return _to_read(calendar, follower_count=0)


@router.get("/me", response_model=list[CalendarRead])
def list_my_calendars(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> list[CalendarRead]:
    """List the caller's own calendars. Organizers/admins only.

    Declared before ``/{slug}`` so the literal ``/me`` path wins.
    """
    calendars = crud.calendar.get_multi_by_owner(db, owner_id=current_user.id)
    counts = crud.calendar.follower_counts(
        db, calendar_ids=[c.id for c in calendars]
    )
    return [
        _to_read(c, follower_count=counts.get(c.id, 0)) for c in calendars
    ]


@router.get("/{slug}", response_model=CalendarWithEvents)
def get_calendar(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> CalendarWithEvents:
    """Public calendar page: details plus upcoming published events.

    Private calendars are only visible to their owner (and admins).
    """
    calendar = crud.calendar.get_by_slug(db, slug=slug)
    is_owner = calendar is not None and current_user is not None and (
        calendar.owner_id == current_user.id
        or current_user.role is UserRole.ADMIN
    )
    if calendar is None or (not calendar.is_public and not is_owner):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found."
        )

    events = crud.calendar.get_upcoming_events(db, calendar_id=calendar.id)
    following = current_user is not None and crud.calendar.is_following(
        db, calendar_id=calendar.id, user_id=current_user.id
    )

    read = CalendarWithEvents.model_validate(calendar)
    read.follower_count = crud.calendar.follower_count(
        db, calendar_id=calendar.id
    )
    read.is_following = following
    read.upcoming_events = [EventRead.model_validate(e) for e in events]
    return read


@router.put("/{calendar_id}", response_model=CalendarRead)
def update_calendar(
    calendar_id: int,
    calendar_in: CalendarUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CalendarRead:
    """Update a calendar. Owner (or admin) only."""
    calendar = _get_owned_calendar(calendar_id, db, current_user)
    calendar = crud.calendar.update(db, db_obj=calendar, obj_in=calendar_in)
    return _to_read(
        calendar,
        follower_count=crud.calendar.follower_count(
            db, calendar_id=calendar.id
        ),
    )


@router.post("/{calendar_id}/follow", status_code=status.HTTP_200_OK)
def follow_calendar(
    calendar_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Follow a calendar. Idempotent. Any authenticated user."""
    calendar = crud.calendar.get(db, id=calendar_id)
    is_owner = calendar is not None and calendar.owner_id == current_user.id
    if calendar is None or (not calendar.is_public and not is_owner):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found."
        )
    crud.calendar.follow(db, calendar_id=calendar.id, user_id=current_user.id)
    return {
        "following": True,
        "follower_count": crud.calendar.follower_count(
            db, calendar_id=calendar.id
        ),
    }


@router.delete("/{calendar_id}/follow", status_code=status.HTTP_200_OK)
def unfollow_calendar(
    calendar_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Unfollow a calendar. Any authenticated user."""
    calendar = crud.calendar.get(db, id=calendar_id)
    if calendar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found."
        )
    crud.calendar.unfollow(db, calendar_id=calendar.id, user_id=current_user.id)
    return {
        "following": False,
        "follower_count": crud.calendar.follower_count(
            db, calendar_id=calendar.id
        ),
    }


@router.get("/{calendar_id}/followers", response_model=list[FollowerRead])
def list_followers(
    calendar_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[FollowerRead]:
    """List a calendar's followers. Owner (or admin) only."""
    _get_owned_calendar(calendar_id, db, current_user)
    links = crud.calendar.get_followers(db, calendar_id=calendar_id)
    return [
        FollowerRead(
            user_id=link.user_id,
            email=link.user.email,
            full_name=link.user.full_name,
            followed_at=link.created_at,
        )
        for link in links
    ]
