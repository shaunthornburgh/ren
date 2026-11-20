"""Admin-only endpoints: platform-wide user and event management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db, require_role
from app.models.event import EventStatus
from app.models.user import User, UserRole
from app.schemas.event import AdminEventRead, EventRead
from app.schemas.user import AdminUserUpdate, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
SearchQuery = Annotated[str | None, Query(max_length=100)]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


def _clean(q: str | None) -> str | None:
    """Trim a search term; blank means no filter."""
    return (q or "").strip() or None


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: AdminUser,
    q: SearchQuery = None,
    role: UserRole | None = None,
    skip: Skip = 0,
    limit: Limit = 50,
) -> list[User]:
    """List and search all users. Admin only."""
    return list(
        crud.user.get_multi_for_admin(
            db, q=_clean(q), role=role, skip=skip, limit=limit
        )
    )


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: AdminUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
) -> User:
    """Change a user's role or active flag. Admin only, never on yourself."""
    user = crud.user.get(db, id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if user.id == current_user.id and (
        (user_in.role is not None and user_in.role is not user.role)
        or user_in.is_active is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't change your own role or deactivate your own account.",
        )
    return crud.user.admin_update(db, db_obj=user, obj_in=user_in)


@router.get("/events", response_model=list[AdminEventRead])
def list_events(
    db: Annotated[Session, Depends(get_db)],
    _: AdminUser,
    q: SearchQuery = None,
    status_filter: Annotated[EventStatus | None, Query(alias="status")] = None,
    skip: Skip = 0,
    limit: Limit = 50,
) -> list[AdminEventRead]:
    """List and search every event in any status. Admin only."""
    events = crud.event.get_multi_for_admin(
        db, q=_clean(q), status=status_filter, skip=skip, limit=limit
    )
    return [
        AdminEventRead(
            **EventRead.model_validate(event).model_dump(),
            organizer_name=crud.user.display_name_for(event.organizer),
        )
        for event in events
    ]
