import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.event import EventRead
from app.schemas.user import (
    PublicUserProfile,
    UserProfileUpdate,
    UserRead,
)

router = APIRouter(prefix="/users", tags=["users"])

# Accepted avatar content types → file extension.
_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _remove_local_avatar(url: str | None) -> None:
    """Best-effort delete of a previously uploaded avatar file we own."""
    if not url:
        return
    prefix = f"{settings.BACKEND_URL}/uploads/"
    if not url.startswith(prefix):
        return
    rel = url[len(prefix):]
    # Guard against path traversal; only touch files under UPLOAD_DIR.
    if ".." in rel:
        return
    try:
        (Path(settings.UPLOAD_DIR) / rel).unlink(missing_ok=True)
    except OSError:
        pass


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
    ext = _AVATAR_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Please upload a JPG, PNG, or WebP.",
        )

    # Read up to the limit + 1 byte so we can detect oversize without loading
    # arbitrarily large files into memory.
    contents = file.file.read(settings.MAX_AVATAR_BYTES + 1)
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty."
        )
    if len(contents) > settings.MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large (max 5 MB).",
        )

    avatars_dir = Path(settings.UPLOAD_DIR) / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (avatars_dir / filename).write_bytes(contents)

    # Clean up the previous avatar, then point the user at the new one.
    _remove_local_avatar(current_user.avatar_url)
    url = f"{settings.BACKEND_URL}/uploads/avatars/{filename}"
    return crud.user.update_profile(
        db, db_obj=current_user, obj_in=UserProfileUpdate(avatar_url=url)
    )


@router.delete("/me/avatar", response_model=UserRead)
def delete_avatar(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Remove the current user's avatar."""
    _remove_local_avatar(current_user.avatar_url)
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
