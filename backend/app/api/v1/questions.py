from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_current_active_user, get_db, load_manageable_event
from app.models.event import Event
from app.models.registration_question import RegistrationQuestion
from app.models.user import User
from app.schemas.registration_question import (
    RegistrationQuestionCreate,
    RegistrationQuestionRead,
    RegistrationQuestionReorder,
    RegistrationQuestionUpdate,
)

router = APIRouter(prefix="/events", tags=["registration-questions"])


def _get_event_or_404(event_id: int, db: Session) -> Event:
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


def _get_owned_event(event_id: int, db: Session, current_user: User) -> Event:
    return load_manageable_event(event_id, db, current_user)


def _get_question_or_404(
    question_id: int, event_id: int, db: Session
) -> RegistrationQuestion:
    question = crud.registration_question.get(db, id=question_id)
    if question is None or question.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found."
        )
    return question


@router.get(
    "/{event_id}/questions", response_model=list[RegistrationQuestionRead]
)
def list_questions(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[RegistrationQuestion]:
    """List an event's registration questions (ordered). Public."""
    _get_event_or_404(event_id, db)
    return list(
        crud.registration_question.get_multi_by_event(db, event_id=event_id)
    )


@router.post(
    "/{event_id}/questions",
    response_model=RegistrationQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    event_id: int,
    question_in: RegistrationQuestionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RegistrationQuestion:
    """Add a registration question. Event owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    return crud.registration_question.create(
        db, obj_in=question_in, event_id=event_id
    )


@router.put(
    "/{event_id}/questions/reorder",
    response_model=list[RegistrationQuestionRead],
)
def reorder_questions(
    event_id: int,
    payload: RegistrationQuestionReorder,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[RegistrationQuestion]:
    """Reorder an event's questions. Owner (or admin) only.

    Declared before ``/{question_id}`` so the literal ``/reorder`` wins.
    """
    _get_owned_event(event_id, db, current_user)

    existing_ids = {
        q.id
        for q in crud.registration_question.get_multi_by_event(
            db, event_id=event_id
        )
    }
    provided = payload.item_ids
    if len(provided) != len(set(provided)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_ids must not contain duplicates.",
        )
    if set(provided) != existing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_ids must match the event's questions exactly.",
        )
    return list(
        crud.registration_question.reorder(
            db, event_id=event_id, item_ids=provided
        )
    )


@router.put(
    "/{event_id}/questions/{question_id}",
    response_model=RegistrationQuestionRead,
)
def update_question(
    event_id: int,
    question_id: int,
    question_in: RegistrationQuestionUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RegistrationQuestion:
    """Update a registration question. Owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    question = _get_question_or_404(question_id, event_id, db)
    return crud.registration_question.update(
        db, db_obj=question, obj_in=question_in
    )


@router.delete(
    "/{event_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_question(
    event_id: int,
    question_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a registration question. Owner (or admin) only."""
    _get_owned_event(event_id, db, current_user)
    question = _get_question_or_404(question_id, event_id, db)
    crud.registration_question.delete(db, db_obj=question)
