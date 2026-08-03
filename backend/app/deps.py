"""Shared FastAPI dependencies.

Routers import request-scoped dependencies (`get_db`, the current-user
resolvers, role guards) from this single module.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.event import Event
from app.models.user import User, UserRole

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "require_role",
    "load_manageable_event",
]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
)

# Like ``oauth2_scheme`` but doesn't 401 when the Authorization header is
# absent — used by endpoints that behave differently for signed-in callers.
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token",
    auto_error=False,
)

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the User from a bearer token, or raise 401."""
    payload = decode_access_token(token)
    if payload is None or (user_id := payload.get("sub")) is None:
        raise _credentials_exc
    try:
        user = crud.user.get(db, id=int(user_id))
    except (TypeError, ValueError):
        raise _credentials_exc
    if user is None:
        raise _credentials_exc
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Like `get_current_user` but rejects deactivated accounts."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return current_user


def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Resolve the current user if a valid token is present, else ``None``.

    Never raises — anonymous callers simply get ``None``.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None or (user_id := payload.get("sub")) is None:
        return None
    try:
        user = crud.user.get(db, id=int(user_id))
    except (TypeError, ValueError):
        return None
    return user if (user and user.is_active) else None


def load_manageable_event(
    event_id: int, db: Session, current_user: User
) -> Event:
    """Load an event and assert the caller may manage it.

    Managers are: admins, the event's creator, and users linked to an accepted
    *manager* host row. Raises 404 if the event is missing, 403 otherwise.
    """
    event = crud.event.get(db, id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    if not crud.event_host.can_manage(db, event=event, user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have manager access to this event.",
        )
    return event


def require_role(*roles: UserRole):
    """Dependency factory guarding an endpoint to the given role(s)."""

    def _checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker
