"""
Notifications repository — data access layer.
"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.modules.notifications.entities import (
    Notification,
    NotificationStatus,
    NotificationType,
)


class NotificationsRepository:
    """Data access for notifications, types and statuses."""

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # Lookup tables
    # ------------------------------------------------------------------

    def get_notification_type_by_name(self, name: str) -> NotificationType | None:
        """Return a notification type by its name."""
        return (
            self._session.query(NotificationType)
            .filter(NotificationType.name == name)
            .first()
        )

    def get_notification_status_by_name(self, name: str) -> NotificationStatus | None:
        """Return a notification status by its name."""
        return (
            self._session.query(NotificationStatus)
            .filter(NotificationStatus.name == name)
            .first()
        )

    # ------------------------------------------------------------------
    # Notifications CRUD
    # ------------------------------------------------------------------

    def create_notification(self, notification: Notification) -> Notification:
        """Persist a new notification."""
        self._session.add(notification)
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def get_notification_by_id(self, notification_id: UUID) -> Notification | None:
        """Return a notification with type and status relationships loaded."""
        return (
            self._session.query(Notification)
            .options(
                joinedload(Notification.notification_type),
                joinedload(Notification.notification_status),
            )
            .filter(Notification.notification_id == notification_id)
            .first()
        )

    def get_notifications_for_user(self, user_id: UUID) -> list[Notification]:
        """Return all notifications for a user, newest first."""
        return (
            self._session.query(Notification)
            .options(
                joinedload(Notification.notification_type),
                joinedload(Notification.notification_status),
            )
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    def get_pending_invitation_notification(
        self, user_id: UUID, reference_id: UUID
    ) -> Notification | None:
        """
        Return a pending notification that points to a specific join request.

        Used to find the matching notification when the user accepts/declines.
        """
        pending_status = self.get_notification_status_by_name("pending")
        if not pending_status:
            return None
        return (
            self._session.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.reference_id == reference_id,
                Notification.reference_type == "group_join_request",
                Notification.notification_status_id
                == pending_status.notification_status_id,
            )
            .first()
        )

    def update_notification_status(
        self, notification: Notification, new_status_name: str
    ) -> Notification:
        """Change the status of an existing notification and persist."""
        status = self.get_notification_status_by_name(new_status_name)
        if status:
            notification.notification_status_id = status.notification_status_id
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def delete_notification(self, notification: Notification) -> None:
        """Permanently delete a notification."""
        self._session.delete(notification)
        self._session.commit()
