from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.crud.ticket import (
    CheckInError,
    TicketAlreadyUsedError,
    TicketCancelledError,
)
from app.deps import get_current_active_user, get_db
from app.models.event import Event
from app.models.ticket import Ticket, normalize_ticket_code
from app.models.user import User
from app.schemas.ticket import (
    CheckInGuest,
    CheckInRequest,
    CheckInResult,
    CheckInStats,
)

router = APIRouter(tags=["check-in"])

_not_found = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found."
)


def _load_check_in_event(event_id: int, db: Session, current_user: User) -> Event:
    """Load an event and assert the caller may check guests in to it."""
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    if not crud.event_host.can_check_in(db, event=event, user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have check-in access to this event.",
        )
    return event


def _to_result(ticket: Ticket) -> CheckInResult:
    return CheckInResult(
        ticket_id=ticket.id,
        code=ticket.code,
        status=ticket.status,
        checked_in_at=ticket.checked_in_at,
        ticket_type_name=ticket.ticket_type.name,
        event_id=ticket.ticket_type.event_id,
        event_title=ticket.ticket_type.event.title,
        guest=CheckInGuest(
            user_id=ticket.owner.id,
            email=ticket.owner.email,
            full_name=ticket.owner.full_name,
        ),
    )


@router.post("/check-in", response_model=CheckInResult)
def check_in(
    body: CheckInRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CheckInResult:
    """Admit a ticket at the door: mark it used and return the guest.

    Only the event's owner, managers, hosts (and admins) may check in. For
    anyone else a real code is indistinguishable from a bogus one (404), so the
    endpoint can't be used to probe for valid tickets.

    Errors: 404 unknown code, 409 already used / cancelled (``detail`` carries
    the ticket so staff can see who and when), 422 wrong event.
    """
    if body.event_id is not None:
        _load_check_in_event(body.event_id, db, current_user)

    ticket = crud.ticket.get_by_code(db, code=normalize_ticket_code(body.code))
    if ticket is None:
        raise _not_found
    event = ticket.ticket_type.event
    if not crud.event_host.can_check_in(db, event=event, user=current_user):
        raise _not_found
    if body.event_id is not None and event.id != body.event_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"This ticket is for a different event: {event.title}.",
        )

    try:
        ticket = crud.ticket.check_in(db, ticket=ticket)
    except (TicketAlreadyUsedError, TicketCancelledError) as exc:
        raise _conflict(exc)
    return _to_result(ticket)


def _conflict(exc: CheckInError) -> HTTPException:
    reason = (
        "already_used"
        if isinstance(exc, TicketAlreadyUsedError)
        else "cancelled"
    )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "message": str(exc),
            "reason": reason,
            "ticket": _to_result(exc.ticket).model_dump(mode="json"),
        },
    )


@router.get("/events/{event_id}/check-in/stats", response_model=CheckInStats)
def check_in_stats(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CheckInStats:
    """How many tickets have been checked in. Check-in staff only."""
    _load_check_in_event(event_id, db, current_user)
    checked_in, total = crud.ticket.count_for_event(db, event_id=event_id)
    return CheckInStats(checked_in=checked_in, total=total)
