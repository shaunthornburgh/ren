from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


def get(db: Session, *, id: int) -> User | None:
    """Fetch a user by primary key."""
    return db.get(User, id)


def get_by_email(db: Session, *, email: str) -> User | None:
    """Fetch a user by email (case-sensitive as stored)."""
    return db.scalar(select(User).where(User.email == email))


def create(
    db: Session, *, obj_in: UserCreate, role: UserRole = UserRole.CUSTOMER
) -> User:
    """Persist a new user with a hashed password."""
    user = User(
        email=obj_in.email,
        full_name=obj_in.full_name,
        hashed_password=hash_password(obj_in.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User | None:
    """Return the user if the email exists and the password matches, else None."""
    user = get_by_email(db, email=email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
