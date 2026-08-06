import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agenda_item import AgendaItem
    from app.models.calendar import Calendar
    from app.models.event_host import EventHost
    from app.models.event_message import EventMessage
    from app.models.faq_item import EventFaqItem
    from app.models.registration_question import RegistrationQuestion
    from app.models.ticket_type import TicketType
    from app.models.user import User


class EventStatus(str, enum.Enum):
    """Lifecycle of an event. Only published events are shown publicly."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Where the event happens. One field for both modes: a Google-formatted
    # address when in person, or the joining URL when online. Long enough to
    # hold a meeting link with query parameters.
    location: Mapped[str | None] = mapped_column(String(512))
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    # Coordinates of the selected Google place. Always NULL for online events.
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    image_url: Mapped[str | None] = mapped_column(String(512))
    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"),
        default=EventStatus.DRAFT,
        nullable=False,
    )

    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organizer: Mapped["User"] = relationship(back_populates="events")

    # Every event belongs to a calendar (owned by the organizer). Deleting the
    # calendar cascades to its events, since events can't be orphaned.
    calendar_id: Mapped[int] = mapped_column(
        ForeignKey("calendars.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    calendar: Mapped["Calendar"] = relationship(back_populates="events")

    ticket_types: Mapped[list["TicketType"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    agenda_items: Mapped[list["AgendaItem"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    faq_items: Mapped[list["EventFaqItem"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    messages: Mapped[list["EventMessage"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    registration_questions: Mapped[list["RegistrationQuestion"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    hosts: Mapped[list["EventHost"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
