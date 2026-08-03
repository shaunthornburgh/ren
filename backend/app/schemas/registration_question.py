from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.registration_question import RegistrationFieldType


class RegistrationQuestionBase(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    field_type: RegistrationFieldType = RegistrationFieldType.TEXT
    required: bool = False
    sort_order: int = 0


class RegistrationQuestionCreate(RegistrationQuestionBase):
    """Payload to create a question. Event is taken from the path."""


class RegistrationQuestionUpdate(BaseModel):
    """Partial update. Every field is optional; only provided ones change."""

    label: str | None = Field(default=None, min_length=1, max_length=255)
    field_type: RegistrationFieldType | None = None
    required: bool | None = None
    sort_order: int | None = None


class RegistrationQuestionRead(RegistrationQuestionBase):
    """Question representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime


class RegistrationQuestionReorder(BaseModel):
    """New ordering for an event's questions, by id.

    ``item_ids`` must contain exactly the event's current question ids;
    ``sort_order`` is set to each id's position in the list.
    """

    item_ids: list[int] = Field(min_length=1)


class RegistrationAnswerInput(BaseModel):
    """One answer submitted with an order."""

    question_id: int
    value: str = ""


class RegistrationAnswerRead(BaseModel):
    """An answer shown to the organizer (with its question's label)."""

    question_id: int
    label: str
    value: str
