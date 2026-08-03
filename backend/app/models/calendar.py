from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class Calendar(Base):
    """A followable collection of events, owned by a user.

    Luma-style: people follow the *calendar* (not the organizer), and get
    notified when a new event is published on it.
    """

    __tablename__ = "calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner: Mapped["User"] = relationship(back_populates="calendars")

    events: Mapped[list["Event"]] = relationship(
        back_populates="calendar",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    follower_links: Mapped[list["CalendarFollower"]] = relationship(
        back_populates="calendar",
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


class CalendarFollower(Base):
    """Association row linking a user to a calendar they follow."""

    __tablename__ = "calendar_followers"
    __table_args__ = (
        UniqueConstraint("calendar_id", "user_id", name="uq_calendar_follower"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    calendar_id: Mapped[int] = mapped_column(
        ForeignKey("calendars.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    calendar: Mapped["Calendar"] = relationship(back_populates="follower_links")
    user: Mapped["User"] = relationship(back_populates="calendar_follows")
