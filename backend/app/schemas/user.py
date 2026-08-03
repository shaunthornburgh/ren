from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.event import EventRead


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Payload for self-registration. Role is fixed to customer server-side."""

    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    """User representation returned to clients (never exposes the password)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    is_active: bool
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class UserProfileUpdate(BaseModel):
    """Fields a user may edit on their own profile."""

    display_name: str | None = Field(default=None, max_length=255)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=512)


class PublicUserProfile(BaseModel):
    """Public profile: safe fields only, plus the events they're hosting.

    ``display_name`` is resolved server-side (never exposes the raw email).
    """

    id: int
    display_name: str
    bio: str | None = None
    avatar_url: str | None = None
    hosting_events: list[EventRead] = []
