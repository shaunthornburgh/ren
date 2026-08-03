from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_current_active_user, get_db, load_manageable_event
from app.models.event import Event
from app.models.faq_item import EventFaqItem
from app.models.user import User
from app.schemas.faq_item import (
    FaqItemCreate,
    FaqItemRead,
    FaqItemUpdate,
    FaqReorder,
)

router = APIRouter(prefix="/events", tags=["faq"])


def _get_event_or_404(event_id: int, db: Session) -> Event:
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


def _get_owned_event(event_id: int, db: Session, current_user: User) -> Event:
    return load_manageable_event(event_id, db, current_user)


def _get_item_or_404(
    item_id: int, event_id: int, db: Session
) -> EventFaqItem:
    item = crud.faq_item.get(db, id=item_id)
    if item is None or item.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="FAQ item not found."
        )
    return item


@router.get("/{event_id}/faq", response_model=list[FaqItemRead])
def list_faq(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[EventFaqItem]:
    """List an event's FAQ items (ordered). Public, no auth required."""
    _get_event_or_404(event_id, db)
    return list(crud.faq_item.get_multi_by_event(db, event_id=event_id))


@router.post(
    "/{event_id}/faq",
    response_model=FaqItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_faq_item(
    event_id: int,
    item_in: FaqItemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EventFaqItem:
    """Add a FAQ item to an event. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    return crud.faq_item.create(db, obj_in=item_in, event_id=event_id)


@router.put("/{event_id}/faq/reorder", response_model=list[FaqItemRead])
def reorder_faq(
    event_id: int,
    payload: FaqReorder,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[EventFaqItem]:
    """Reorder an event's FAQ items. Event owner (or admin) only.

    Declared before ``/{item_id}`` so the literal ``/reorder`` path wins.
    ``item_ids`` must contain exactly the event's current FAQ item ids.
    """
    _get_owned_event(event_id, db, current_user)

    existing_ids = {
        item.id
        for item in crud.faq_item.get_multi_by_event(db, event_id=event_id)
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
            detail="item_ids must match the event's FAQ items exactly.",
        )
    return list(
        crud.faq_item.reorder(db, event_id=event_id, item_ids=provided)
    )


@router.put("/{event_id}/faq/{item_id}", response_model=FaqItemRead)
def update_faq_item(
    event_id: int,
    item_id: int,
    item_in: FaqItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EventFaqItem:
    """Update a FAQ item. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    item = _get_item_or_404(item_id, event_id, db)
    return crud.faq_item.update(db, db_obj=item, obj_in=item_in)


@router.delete(
    "/{event_id}/faq/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_faq_item(
    event_id: int,
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a FAQ item. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    item = _get_item_or_404(item_id, event_id, db)
    crud.faq_item.delete(db, db_obj=item)
