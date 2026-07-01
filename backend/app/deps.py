"""Shared FastAPI dependencies.

`get_db` is re-exported here so routers can import all request dependencies
from a single module. The current-user dependencies are intentionally left as
placeholders until the User model and CRUD layer exist; uncomment them once the
auth module lands.
"""

from app.core.database import get_db

__all__ = ["get_db"]

# from typing import Annotated
#
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from sqlalchemy.orm import Session
#
# from app.core.security import decode_access_token
#
# oauth2_scheme = OAuth2PasswordBearer(
#     tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
# )
#
#
# def get_current_user(
#     token: Annotated[str, Depends(oauth2_scheme)],
#     db: Annotated[Session, Depends(get_db)],
# ):
#     credentials_exc = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     payload = decode_access_token(token)
#     if payload is None or (user_id := payload.get("sub")) is None:
#         raise credentials_exc
#     user = crud.user.get(db, id=int(user_id))
#     if user is None:
#         raise credentials_exc
#     return user
