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
from app.models.user import User, UserRole

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "require_role",
]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
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
