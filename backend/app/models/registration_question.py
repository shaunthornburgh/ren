import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.order import Order


class RegistrationFieldType(str, enum.Enum):
    """Input type for a custom registration question."""

    TEXT = "text"
    TEXTAREA = "textarea"
    URL = "url"


class RegistrationQuestion(Base):
    """A custom question an organizer asks registrants during purchase."""

    __tablename__ = "registration_questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event: Mapped["Event"] = relationship(back_populates="registration_questions")

    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[RegistrationFieldType] = mapped_column(
        Enum(RegistrationFieldType, name="registration_field_type"),
        default=RegistrationFieldType.TEXT,
        nullable=False,
    )
    required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
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


class RegistrationAnswer(Base):
    """A registrant's answer to a custom question, tied to their order."""

    __tablename__ = "registration_answers"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "question_id", name="uq_registration_answer"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order: Mapped["Order"] = relationship(back_populates="registration_answers")

    question_id: Mapped[int] = mapped_column(
        ForeignKey("registration_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question: Mapped["RegistrationQuestion"] = relationship()

    value: Mapped[str] = mapped_column(Text, nullable=False)
