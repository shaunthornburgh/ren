from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.notification import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    unread_only: Annotated[bool, Query()] = False,
) -> list[NotificationRead]:
    """List the current user's notifications, newest first."""
    return list(
        crud.notification.get_multi_by_user(
            db, user_id=current_user.id, unread_only=unread_only
        )
    )


@router.get("/unread-count")
def unread_count(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Number of unread notifications for the current user."""
    return {"unread": crud.notification.unread_count(db, user_id=current_user.id)}


@router.post("/read-all")
def mark_all_read(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Mark all of the current user's notifications as read."""
    updated = crud.notification.mark_all_read(db, user_id=current_user.id)
    return {"updated": updated}
