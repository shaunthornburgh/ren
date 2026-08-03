from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import (
    get_current_active_user,
    get_current_user_optional,
    get_db,
    load_manageable_event,
)
from app.models.event import Event
from app.models.event_host import EventHost, HostRole, HostStatus
from app.models.user import User
from app.schemas.event_host import (
    EventHostCreate,
    EventHostRead,
    EventHostUpdate,
    PublicHostRead,
)

router = APIRouter(prefix="/events", tags=["hosts"])


def _get_event_or_404(event_id: int, db: Session) -> Event:
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


def _get_host_or_404(host_id: int, event_id: int, db: Session) -> EventHost:
    host = crud.event_host.get(db, id=host_id)
    if host is None or host.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found."
        )
    return host


def _creator_entry(event: Event) -> EventHostRead:
    """A synthetic, non-removable host row representing the event creator."""
    creator = event.organizer
    return EventHostRead(
        id=0,
        event_id=event.id,
        user_id=creator.id,
        email=creator.email,
        name=creator.full_name,
        role=HostRole.MANAGER,
        show_on_page=False,
        status=HostStatus.ACCEPTED,
        is_creator=True,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("/{event_id}/hosts", response_model=None)
def list_hosts(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> list[EventHostRead] | list[PublicHostRead]:
    """List an event's hosts.

    Managers see every host (plus the implicit creator); everyone else sees
    only hosts flagged ``show_on_page``.
    """
    event = _get_event_or_404(event_id, db)
    is_manager = current_user is not None and crud.event_host.can_manage(
        db, event=event, user=current_user
    )

    if is_manager:
        rows: list[EventHostRead] = [_creator_entry(event)]
        for host in crud.event_host.get_multi_by_event(db, event_id=event_id):
            # The creator is already shown as the synthetic entry above.
            if host.user_id == event.organizer_id or (
                host.email == event.organizer.email
            ):
                continue
            read = EventHostRead.model_validate(host)
            rows.append(read)
        return rows

    return [
        PublicHostRead(
            user_id=host.user_id,
            name=host.name,
            email=host.email,
            role=host.role,
        )
        for host in crud.event_host.get_public_by_event(db, event_id=event_id)
    ]


@router.post(
    "/{event_id}/hosts",
    response_model=EventHostRead,
    status_code=status.HTTP_201_CREATED,
)
def add_host(
    event_id: int,
    host_in: EventHostCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EventHost:
    """Invite a host by email. Managers only."""
    load_manageable_event(event_id, db, current_user)
    if crud.event_host.get_by_event_and_email(
        db, event_id=event_id, email=str(host_in.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A host with this email already exists for the event.",
        )
    return crud.event_host.create(db, obj_in=host_in, event_id=event_id)


@router.put("/{event_id}/hosts/{host_id}", response_model=EventHostRead)
def update_host(
    event_id: int,
    host_id: int,
    host_in: EventHostUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EventHost:
    """Update a host. Managers only."""
    load_manageable_event(event_id, db, current_user)
    host = _get_host_or_404(host_id, event_id, db)
    return crud.event_host.update(db, db_obj=host, obj_in=host_in)


@router.delete(
    "/{event_id}/hosts/{host_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_host(
    event_id: int,
    host_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Remove a host. Managers only; the event creator can't be removed."""
    event = load_manageable_event(event_id, db, current_user)
    host = _get_host_or_404(host_id, event_id, db)
    if host.user_id is not None and host.user_id == event.organizer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The event creator cannot be removed.",
        )
    crud.event_host.delete(db, db_obj=host)
