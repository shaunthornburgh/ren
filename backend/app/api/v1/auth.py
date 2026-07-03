from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.core.security import create_access_token
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> Token:
    """Build an access token embedding the user's role."""
    access_token = create_access_token(
        subject=user.id, extra_claims={"role": user.role.value}
    )
    return Token(access_token=access_token)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Register a new customer account."""
    if crud.user.get_by_email(db, email=user_in.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    return crud.user.create(db, obj_in=user_in)


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Authenticate with email + password and return a bearer token."""
    user = crud.user.authenticate(
        db, email=credentials.email, password=credentials.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    return _token_for(user)


@router.post("/token", response_model=Token, include_in_schema=False)
def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """OAuth2 password-flow endpoint backing Swagger's Authorize button.

    Uses the standard form fields (`username` = email, `password`).
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_for(user)


@router.get("/me", response_model=UserRead)
def read_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the currently authenticated user."""
    return current_user
