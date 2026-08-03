from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app import crud
from app.core import email
from app.deps import (
    get_current_active_user,
    get_db,
    load_manageable_event,
    require_role,
)
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
    OrganizerEventRead,
)
from app.schemas.guest import GuestRead, GuestTicketLine
from app.schemas.registration_question import RegistrationAnswerRead

router = APIRouter(prefix="/events", tags=["events"])


def _get_owned_event(
    event_id: int, db: Session, current_user: User
) -> Event:
    """Load an event and assert the caller may manage it (creator/manager/admin)."""
    return load_manageable_event(event_id, db, current_user)


def _assert_calendar_owned(
    calendar_id: int, db: Session, current_user: User
) -> None:
    """Ensure the caller may attach events to the given calendar."""
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


def _notify_followers(
    db: Session, event: Event, background_tasks: BackgroundTasks
) -> None:
    """Fan out in-app notifications now and schedule follower emails."""
    batch = crud.notification.notify_new_event(db, event=event)
    if batch is not None and batch.recipient_emails:
        background_tasks.add_task(email.send_new_event_emails, batch)


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event_in: EventCreate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> Event:
    """Create a new event. Organizers (and admins) only.

    Every event belongs to a calendar the caller owns. If it's created already
    published, the calendar's followers are notified (in-app + email).
    """
    _assert_calendar_owned(event_in.calendar_id, db, current_user)
    event = crud.event.create(
        db, obj_in=event_in, organizer_id=current_user.id
    )
    if event.status is EventStatus.PUBLISHED:
        _notify_followers(db, event, background_tasks)
    return event


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


@router.get("/{event_id}/guests", response_model=list[GuestRead])
def list_event_guests(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[GuestRead]:
    """List people who ordered tickets for this event. Owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)

    guests: list[GuestRead] = []
    for order in crud.order.get_event_guests(db, event_id=event_id):
        # An order may span multiple events; keep only this event's lines.
        lines = [
            GuestTicketLine(
                ticket_type_name=item.ticket_type.name, quantity=item.quantity
            )
            for item in order.items
            if item.ticket_type.event_id == event_id
        ]
        if not lines:
            continue
        answers = [
            RegistrationAnswerRead(
                question_id=answer.question_id,
                label=answer.question.label,
                value=answer.value,
            )
            for answer in order.registration_answers
            if answer.question is not None
            and answer.question.event_id == event_id
        ]
        guests.append(
            GuestRead(
                order_id=order.id,
                status=order.status,
                created_at=order.created_at,
                email=order.user.email,
                full_name=order.user.full_name,
                total_quantity=sum(line.quantity for line in lines),
                items=lines,
                answers=answers,
            )
        )
    return guests


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Event:
    """Update an event. Owner (or admin) only.

    When an event first transitions to *published*, its calendar's followers
    are notified (in-app + email).
    """
    event = _get_owned_event(event_id, db, current_user)

    # calendar_id can be re-pointed but never cleared (it's required).
    if "calendar_id" in event_in.model_fields_set:
        if event_in.calendar_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="calendar_id cannot be null.",
            )
        _assert_calendar_owned(event_in.calendar_id, db, current_user)

    was_published = event.status is EventStatus.PUBLISHED
    event = crud.event.update(db, db_obj=event, obj_in=event_in)

    if not was_published and event.status is EventStatus.PUBLISHED:
        _notify_followers(db, event, background_tasks)
    return event
