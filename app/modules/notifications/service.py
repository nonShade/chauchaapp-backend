"""
Notifications service — business logic layer.
"""

from uuid import UUID

from app.modules.notifications.dto import NotificationResponseDTO
from app.modules.notifications.repository import NotificationsRepository
from app.shared.exceptions import ForbiddenException, NotFoundException


class NotificationsService:
    """Business logic for user notifications."""

    def __init__(self, repository: NotificationsRepository):
        self._repo = repository

    def get_my_notifications(self, user_id: UUID) -> list[NotificationResponseDTO]:
        """Return all notifications for the authenticated user, newest first."""
        notifications = self._repo.get_notifications_for_user(user_id)
        return [self._map_to_dto(n) for n in notifications]

    def delete_notification(self, user_id: UUID, notification_id: UUID) -> None:
        """Permanently delete a notification that belongs to the user.

        Raises:
            NotFoundException: if notification does not exist.
            ForbiddenException: if it belongs to a different user.
        """
        notification = self._repo.get_notification_by_id(notification_id)
        if not notification:
            raise NotFoundException("Notificación no encontrada")
        if notification.user_id != user_id:
            raise ForbiddenException(
                "No tienes permiso para eliminar esta notificación"
            )
        self._repo.delete_notification(notification)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _map_to_dto(self, notification) -> NotificationResponseDTO:
        return NotificationResponseDTO(
            notification_id=notification.notification_id,
            user_id=notification.user_id,
            notification_type=(
                notification.notification_type.name
                if notification.notification_type
                else ""
            ),
            notification_status=(
                notification.notification_status.name
                if notification.notification_status
                else ""
            ),
            message=notification.message,
            scheduled_date=notification.scheduled_date,
            reference_id=notification.reference_id,
            reference_type=notification.reference_type,
        )
