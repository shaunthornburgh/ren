from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationRead(BaseModel):
    """An in-app notification for the current user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    title: str
    message: str | None = None
    event_id: int | None = None
    calendar_id: int | None = None
    is_read: bool
    created_at: datetime
