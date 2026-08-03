import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class HostRole(str, enum.Enum):
    """A host's role on an event."""

    MANAGER = "manager"  # can manage the event (once user_id is set)
    HOST = "host"  # display-only host


class HostStatus(str, enum.Enum):
    """Whether an invited host has a linked account yet."""

    PENDING = "pending"  # invited by email, no matching account yet
    ACCEPTED = "accepted"  # linked to a user account


class EventHost(Base):
    """A person invited to co-host or co-manage an event, by email.

    Hosts are independent of the event's calendar. A host may be invited before
    they have an account (``user_id`` null, ``status`` pending); the row is
    linked to a user once one with the matching email registers or logs in.
    """

    __tablename__ = "event_hosts"
    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_event_host_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event: Mapped["Event"] = relationship(back_populates="hosts")

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    user: Mapped["User | None"] = relationship()

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[HostRole] = mapped_column(
        Enum(HostRole, name="host_role"),
        default=HostRole.HOST,
        nullable=False,
    )
    show_on_page: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    status: Mapped[HostStatus] = mapped_column(
        Enum(HostStatus, name="host_status"),
        default=HostStatus.PENDING,
        nullable=False,
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
