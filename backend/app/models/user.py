import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.calendar import Calendar, CalendarFollower
    from app.models.event import Event
    from app.models.notification import Notification
    from app.models.order import Order
    from app.models.ticket import Ticket


class UserRole(str, enum.Enum):
    """Application roles. Customers are the default; organizers manage events."""

    CUSTOMER = "customer"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.CUSTOMER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Public profile fields (all optional).
    display_name: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    events: Mapped[list["Event"]] = relationship(
        back_populates="organizer",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    calendars: Mapped[list["Calendar"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    calendar_follows: Mapped[list["CalendarFollower"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
