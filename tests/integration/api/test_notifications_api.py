"""
Integration tests for the Notifications API endpoints.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.modules.notifications.entities import Notification, NotificationStatus, NotificationType
from app.modules.users.entities import User
from app.shared.security.auth_middleware import get_current_user
from main import app


def _mock_user(user_id=None):
    u = MagicMock(spec=User)
    u.user_id = user_id or uuid.uuid4()
    return u


def _mock_notification(notif_id=None, user_id=None):
    n = MagicMock(spec=Notification)
    n.notification_id = notif_id or uuid.uuid4()
    n.user_id = user_id or uuid.uuid4()
    n.message = "Test message"
    n.scheduled_date = None
    n.reference_id = None
    n.reference_type = None

    t = MagicMock(spec=NotificationType)
    t.name = "group_join_request"
    n.notification_type = t

    s = MagicMock(spec=NotificationStatus)
    s.name = "pending"
    n.notification_status = s

    return n


# ---------------------------------------------------------------------------
# GET /v1/notifications — List notifications
# ---------------------------------------------------------------------------


def test_get_my_notifications(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    notif = _mock_notification(user_id=user_id)

    mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
        notif
    ]

    response = client.get("/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["notification_id"] == str(notif.notification_id)
    assert data[0]["message"] == "Test message"


# ---------------------------------------------------------------------------
# DELETE /v1/notifications/{id} — Delete notification
# ---------------------------------------------------------------------------


def test_delete_notification_success(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    notif_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    notif = _mock_notification(notif_id=notif_id, user_id=user_id)
    
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = notif

    response = client.delete(f"/v1/notifications/{notif_id}")
    assert response.status_code == 204


def test_delete_notification_not_found(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

    response = client.delete(f"/v1/notifications/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_notification_wrong_user(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    notif_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    notif = _mock_notification(notif_id=notif_id, user_id=other_user_id)
    
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = notif

    response = client.delete(f"/v1/notifications/{notif_id}")
    assert response.status_code == 403
