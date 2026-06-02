"""
Notifications module DTOs.

Handles data transfer formatting for Notification endpoints.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationResponseDTO(BaseModel):
    """Full notification record returned to the client."""

    notification_id: UUID
    user_id: UUID
    notification_type: str
    notification_status: str
    message: str | None
    scheduled_date: date | None
    created_at: datetime
    reference_id: UUID | None
    reference_type: str | None

    model_config = {"from_attributes": True}
