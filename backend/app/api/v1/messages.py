from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app import crud
from app.core import email
from app.deps import get_current_active_user, get_db, load_manageable_event
from app.models.event import Event
from app.models.event_message import EventMessage
from app.models.user import User
from app.schemas.event_message import EventMessageCreate, EventMessageRead

router = APIRouter(prefix="/events", tags=["messages"])


def _get_owned_event(event_id: int, db: Session, current_user: User) -> Event:
    """Load an event and assert the caller may manage it."""
    return load_manageable_event(event_id, db, current_user)


@router.get("/{event_id}/messages", response_model=list[EventMessageRead])
def list_messages(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[EventMessage]:
    """List an event's sent messages (history). Owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    return list(crud.event_message.get_multi_by_event(db, event_id=event_id))


@router.post(
    "/{event_id}/messages",
    response_model=EventMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    event_id: int,
    message_in: EventMessageCreate,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EventMessage:
    """Broadcast a message to the event's guests (those with a paid order).

    The message is recorded for history and delivered in the background, so a
    mail failure never fails the request.
    """
    event = _get_owned_event(event_id, db, current_user)

    recipients = crud.order.get_event_recipient_emails(db, event_id=event_id)

    message = crud.event_message.create(
        db,
        obj_in=message_in,
        event_id=event_id,
        sent_by_id=current_user.id,
        recipient_count=len(recipients),
    )

    if recipients:
        background_tasks.add_task(
            email.send_event_message,
            subject=message_in.subject,
            body=message_in.body,
            recipients=recipients,
            event_id=event_id,
            event_title=event.title,
        )
    return message
