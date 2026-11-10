from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_type import TicketType


class CheckInError(Exception):
    """Base class for a ticket that can't be checked in."""

    def __init__(self, message: str, ticket: Ticket) -> None:
        super().__init__(message)
        self.ticket = ticket


class TicketAlreadyUsedError(CheckInError):
    """The ticket was already checked in."""


class TicketCancelledError(CheckInError):
    """The ticket was cancelled and is no longer valid."""


def get_by_code(db: Session, *, code: str) -> Ticket | None:
    """Fetch a ticket by its check-in code, with its type, event and owner."""
    stmt = (
        select(Ticket)
        .where(Ticket.code == code)
        .options(
            joinedload(Ticket.ticket_type).joinedload(TicketType.event),
            joinedload(Ticket.owner),
        )
    )
    return db.scalars(stmt).first()


def check_in(db: Session, *, ticket: Ticket) -> Ticket:
    """Mark a VALID ticket USED, recording when it was checked in.

    The row is re-read under a lock so two scanners presenting the same ticket
    at once can't both admit it: the second sees USED and is rejected.
    """
    try:
        locked = db.scalars(
            select(Ticket)
            .where(Ticket.id == ticket.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()
        if locked.status is TicketStatus.USED:
            raise TicketAlreadyUsedError(
                "This ticket has already been checked in.", locked
            )
        if locked.status is TicketStatus.CANCELLED:
            raise TicketCancelledError(
                "This ticket has been cancelled.", locked
            )

        locked.status = TicketStatus.USED
        locked.checked_in_at = func.now()
        db.commit()
        db.refresh(locked)
        return locked
    except Exception:
        db.rollback()
        raise


def count_for_event(db: Session, *, event_id: int) -> tuple[int, int]:
    """(checked-in, admissible) ticket counts for an event.

    Admissible means VALID or USED — cancelled tickets aren't expected at the
    door.
    """
    rows = db.execute(
        select(Ticket.status, func.count())
        .join(Ticket.ticket_type)
        .where(TicketType.event_id == event_id)
        .group_by(Ticket.status)
    ).all()
    counts = {status: n for status, n in rows}
    used = counts.get(TicketStatus.USED, 0)
    return used, used + counts.get(TicketStatus.VALID, 0)
