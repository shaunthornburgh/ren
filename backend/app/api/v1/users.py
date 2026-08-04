from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.uploads import remove_local_upload, save_image_upload
from app.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.event import EventRead
from app.schemas.user import (
    PublicUserProfile,
    UserProfileUpdate,
    UserRead,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_my_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Return the current user's own profile (editable fields included)."""
    return current_user


@router.patch("/me", response_model=UserRead)
def update_my_profile(
    profile_in: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Update the current user's public profile fields."""
    return crud.user.update_profile(db, db_obj=current_user, obj_in=profile_in)


@router.post("/me/avatar", response_model=UserRead)
def upload_avatar(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: Annotated[UploadFile, File()],
) -> User:
    """Upload a new avatar image (JPG/PNG/WebP, max 5 MB) for the current user."""
    url = save_image_upload(
        file=file, subdir="avatars", max_bytes=settings.MAX_AVATAR_BYTES
    )
    # Clean up the previous avatar, then point the user at the new one.
    remove_local_upload(current_user.avatar_url)
    return crud.user.update_profile(
        db, db_obj=current_user, obj_in=UserProfileUpdate(avatar_url=url)
    )


@router.delete("/me/avatar", response_model=UserRead)
def delete_avatar(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Remove the current user's avatar."""
    remove_local_upload(current_user.avatar_url)
    current_user.avatar_url = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=PublicUserProfile)
def read_public_profile(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> PublicUserProfile:
    """Public profile: basic info plus upcoming events this user hosts.

    Declared after ``/me`` so the literal path wins. No authentication required.
    """
    user = crud.user.get(db, id=user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    events = crud.event.get_upcoming_hosted_by_user(db, user_id=user_id)
    return PublicUserProfile(
        id=user.id,
        display_name=crud.user.display_name_for(user),
        bio=user.bio,
        avatar_url=user.avatar_url,
        hosting_events=[EventRead.model_validate(e) for e in events],
    )
