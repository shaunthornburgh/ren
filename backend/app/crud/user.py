from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import AdminUserUpdate, UserCreate, UserProfileUpdate


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


def update_profile(
    db: Session, *, db_obj: User, obj_in: UserProfileUpdate
) -> User:
    """Apply a partial update to a user's public profile fields."""
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def display_name_for(user: User) -> str:
    """Resolve a public display name without exposing the raw email."""
    return (
        user.display_name
        or user.full_name
        or user.email.split("@")[0]
    )


def authenticate(db: Session, *, email: str, password: str) -> User | None:
    """Return the user if the email exists and the password matches, else None."""
    user = get_by_email(db, email=email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def get_multi_for_admin(
    db: Session,
    *,
    q: str | None = None,
    role: UserRole | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Sequence[User]:
    """List users newest first, optionally searched by name/email and role."""
    stmt = select(User)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    if role is not None:
        stmt = stmt.where(User.role == role)
    stmt = (
        stmt.order_by(User.created_at.desc(), User.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def admin_update(db: Session, *, db_obj: User, obj_in: AdminUserUpdate) -> User:
    """Apply an admin's partial update to a user's role / active flag."""
    data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
