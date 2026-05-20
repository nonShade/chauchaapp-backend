"""
Notifications controller — HTTP endpoint layer.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.modules.notifications.dto import NotificationResponseDTO
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import NotificationsService
from app.modules.users.entities import User
from app.shared.database import get_db
from app.shared.security.auth_middleware import get_current_user

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])


def _get_notifications_service(
    db: Session = Depends(get_db),
) -> NotificationsService:
    """Dependency builder for NotificationsService."""
    return NotificationsService(NotificationsRepository(db))


@router.get(
    "",
    response_model=list[NotificationResponseDTO],
    summary="Mis notificaciones",
    description="Retorna todas las notificaciones del usuario autenticado, ordenadas de más reciente a más antigua.",
)
def get_my_notifications(
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(_get_notifications_service),
):
    """List all notifications for the current user."""
    return service.get_my_notifications(user.user_id)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar notificación",
    description="Elimina permanentemente una notificación del usuario autenticado.",
)
def delete_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(_get_notifications_service),
):
    """Permanently delete a notification."""
    service.delete_notification(user.user_id, notification_id)
    return
