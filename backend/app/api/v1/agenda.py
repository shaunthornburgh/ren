from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db, require_role
from app.models.agenda_item import AgendaItem
from app.models.event import Event
from app.models.user import User, UserRole
from app.schemas.agenda_item import (
    AgendaItemCreate,
    AgendaItemRead,
    AgendaItemUpdate,
    AgendaReorder,
)

router = APIRouter(prefix="/events", tags=["agenda"])


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


def _get_item_or_404(
    item_id: int, event_id: int, db: Session
) -> AgendaItem:
    """Load an agenda item, ensuring it belongs to the given event."""
    item = crud.agenda_item.get(db, id=item_id)
    if item is None or item.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found.",
        )
    return item


@router.get("/{event_id}/agenda", response_model=list[AgendaItemRead])
def list_agenda(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[AgendaItem]:
    """List an event's agenda items (ordered). Public, no auth required."""
    _get_event_or_404(event_id, db)
    return list(crud.agenda_item.get_multi_by_event(db, event_id=event_id))


@router.post(
    "/{event_id}/agenda",
    response_model=AgendaItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_agenda_item(
    event_id: int,
    item_in: AgendaItemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> AgendaItem:
    """Add an agenda item to an event. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    return crud.agenda_item.create(db, obj_in=item_in, event_id=event_id)


@router.put(
    "/{event_id}/agenda/reorder",
    response_model=list[AgendaItemRead],
)
def reorder_agenda(
    event_id: int,
    payload: AgendaReorder,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> list[AgendaItem]:
    """Reorder an event's agenda items. Event owner (or admin) only.

    Declared before ``/{item_id}`` so the literal ``/reorder`` path wins.
    ``item_ids`` must contain exactly the event's current agenda item ids.
    """
    _get_owned_event(event_id, db, current_user)

    existing_ids = {
        item.id
        for item in crud.agenda_item.get_multi_by_event(db, event_id=event_id)
    }
    provided = payload.item_ids
    if len(provided) != len(set(provided)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_ids must not contain duplicates.",
        )
    if set(provided) != existing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_ids must match the event's agenda items exactly.",
        )

    return list(
        crud.agenda_item.reorder(db, event_id=event_id, item_ids=provided)
    )


@router.put(
    "/{event_id}/agenda/{item_id}",
    response_model=AgendaItemRead,
)
def update_agenda_item(
    event_id: int,
    item_id: int,
    item_in: AgendaItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> AgendaItem:
    """Update an agenda item. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    item = _get_item_or_404(item_id, event_id, db)
    return crud.agenda_item.update(db, db_obj=item, obj_in=item_in)


@router.delete(
    "/{event_id}/agenda/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_agenda_item(
    event_id: int,
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
    ],
) -> None:
    """Delete an agenda item. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    item = _get_item_or_404(item_id, event_id, db)
    crud.agenda_item.delete(db, db_obj=item)
