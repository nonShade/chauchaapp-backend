"""
Unit tests for NotificationsService.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.modules.notifications.entities import (
    Notification,
    NotificationStatus,
    NotificationType,
)
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import NotificationsService
from app.shared.exceptions import ForbiddenException, NotFoundException


@pytest.fixture
def mock_repo():
    return MagicMock(spec=NotificationsRepository)


@pytest.fixture
def service(mock_repo):
    return NotificationsService(mock_repo)


def _make_notification(notif_id=None, user_id=None):
    n = MagicMock(spec=Notification)
    n.notification_id = notif_id or uuid.uuid4()
    n.user_id = user_id or uuid.uuid4()
    n.message = "Test notification"
    n.scheduled_date = None
    n.reference_id = None
    n.reference_type = None

    type_mock = MagicMock(spec=NotificationType)
    type_mock.name = "group_join_request"
    n.notification_type = type_mock

    status_mock = MagicMock(spec=NotificationStatus)
    status_mock.name = "pending"
    n.notification_status = status_mock

    return n


class TestGetMyNotifications:
    def test_returns_notifications_for_user(self, service, mock_repo):
        user_id = uuid.uuid4()
        n1 = _make_notification(user_id=user_id)
        n2 = _make_notification(user_id=user_id)
        mock_repo.get_notifications_for_user.return_value = [n1, n2]

        result = service.get_my_notifications(user_id)

        assert len(result) == 2
        mock_repo.get_notifications_for_user.assert_called_once_with(user_id)

    def test_returns_empty_list_if_no_notifications(self, service, mock_repo):
        user_id = uuid.uuid4()
        mock_repo.get_notifications_for_user.return_value = []

        result = service.get_my_notifications(user_id)

        assert result == []

    def test_dto_fields_are_correctly_mapped(self, service, mock_repo):
        user_id = uuid.uuid4()
        notif = _make_notification(user_id=user_id)
        mock_repo.get_notifications_for_user.return_value = [notif]

        result = service.get_my_notifications(user_id)

        assert result[0].notification_type == "group_join_request"
        assert result[0].notification_status == "pending"
        assert result[0].user_id == user_id


class TestDeleteNotification:
    def test_deletes_own_notification(self, service, mock_repo):
        user_id = uuid.uuid4()
        notif = _make_notification(user_id=user_id)
        mock_repo.get_notification_by_id.return_value = notif

        service.delete_notification(user_id, notif.notification_id)

        mock_repo.delete_notification.assert_called_once_with(notif)

    def test_raises_if_notification_not_found(self, service, mock_repo):
        mock_repo.get_notification_by_id.return_value = None

        with pytest.raises(NotFoundException):
            service.delete_notification(uuid.uuid4(), uuid.uuid4())

    def test_raises_if_notification_belongs_to_other_user(self, service, mock_repo):
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        notif = _make_notification(user_id=other_user_id)
        mock_repo.get_notification_by_id.return_value = notif

        with pytest.raises(ForbiddenException):
            service.delete_notification(user_id, notif.notification_id)
