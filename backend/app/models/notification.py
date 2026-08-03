import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """Kinds of notification the system can raise."""

    EVENT_PUBLISHED = "event_published"


class Notification(Base):
    """An in-app notification delivered to a single user.

    MVP delivery is just this record (surfaced in the UI / logged). Email or
    push can be layered on later by consuming unread rows.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)

    # Optional context — kept nullable so a deleted event/calendar leaves the
    # notification intact (ForeignKey uses SET NULL).
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    calendar_id: Mapped[int | None] = mapped_column(
        ForeignKey("calendars.id", ondelete="SET NULL")
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notifications")
