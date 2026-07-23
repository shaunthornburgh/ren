from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_current_active_user, get_db, require_role
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
    OrganizerEventRead,
)

router = APIRouter(prefix="/events", tags=["events"])


def _get_owned_event(
    event_id: int, db: Session, current_user: User
) -> Event:
    """Load an event and assert the caller owns it (admins bypass)."""
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    if (
        event.organizer_id != current_user.id
        and current_user.role is not UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this event.",
        )
    return event


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event_in: EventCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> Event:
    """Create a new event. Organizers (and admins) only."""
    return crud.event.create(db, obj_in=event_in, organizer_id=current_user.id)


@router.get("", response_model=list[EventRead])
def list_events(
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Event]:
    """List published events. Public, no authentication required."""
    return list(
        crud.event.get_multi(
            db, skip=skip, limit=limit, status=EventStatus.PUBLISHED
        )
    )


@router.get("/me", response_model=list[OrganizerEventRead])
def list_my_events(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> list[OrganizerEventRead]:
    """List the caller's own events with sales stats. Organizers/admins only.

    Declared before ``/{event_id}`` so the literal ``/me`` path wins.
    """
    rows = crud.event.get_multi_by_organizer_with_stats(
        db, organizer_id=current_user.id
    )
    return [
        OrganizerEventRead(**EventRead.model_validate(event).model_dump(), **stats)
        for event, stats in rows
    ]


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Event:
    """Fetch a single event by id. Public."""
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Event:
    """Update an event. Owner (or admin) only."""
    event = _get_owned_event(event_id, db, current_user)
    return crud.event.update(db, db_obj=event, obj_in=event_in)
