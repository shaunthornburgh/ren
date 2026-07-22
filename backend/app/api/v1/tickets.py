from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db, require_role
from app.models.event import Event
from app.models.ticket_type import TicketType
from app.models.user import User, UserRole
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeRead

router = APIRouter(prefix="/events", tags=["ticket-types"])


def _get_event_or_404(event_id: int, db: Session) -> Event:
    """Load an event or raise 404."""
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


def _get_owned_event(event_id: int, db: Session, current_user: User) -> Event:
    """Load an event and assert the caller owns it (admins bypass)."""
    event = _get_event_or_404(event_id, db)
    if (
        event.organizer_id != current_user.id
        and current_user.role is not UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this event.",
        )
    return event


@router.get("/{event_id}/ticket-types", response_model=list[TicketTypeRead])
def list_ticket_types(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TicketType]:
    """List ticket types for an event. Public, no authentication required."""
    _get_event_or_404(event_id, db)
    return list(
        crud.ticket_type.get_multi_by_event(
            db, event_id=event_id, skip=skip, limit=limit
        )
    )


@router.post(
    "/{event_id}/ticket-types",
    response_model=TicketTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_type(
    event_id: int,
    ticket_type_in: TicketTypeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> TicketType:
    """Create a ticket type for an event. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    return crud.ticket_type.create(db, obj_in=ticket_type_in, event_id=event_id)
