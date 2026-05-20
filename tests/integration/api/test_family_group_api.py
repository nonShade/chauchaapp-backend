"""
Integration tests for the Family Group API endpoints.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.modules.groups.entities import FamilyGroup, GroupJoinRequest, GroupMember
from app.modules.notifications.entities import Notification, NotificationStatus, NotificationType
from app.modules.users.entities import User
from app.shared.security.auth_middleware import get_current_user
from main import app


def _mock_user(user_id=None):
    u = MagicMock(spec=User)
    u.user_id = user_id or uuid.uuid4()
    u.first_name = "Test"
    u.last_name = "User"
    u.email = "test@test.cl"
    return u


def _mock_group(group_id=None, admin_id=None, name="Mi Grupo"):
    g = MagicMock(spec=FamilyGroup)
    g.family_group_id = group_id or uuid.uuid4()
    g.admin_id = admin_id or uuid.uuid4()
    g.name = name
    admin = _mock_user(user_id=g.admin_id)
    g.admin = admin
    g.members = []
    return g


# ---------------------------------------------------------------------------
# POST /v1/family-group — Create group
# ---------------------------------------------------------------------------


def test_create_family_group_success(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    mock_user = _mock_user(user_id=user_id)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    group_id = uuid.uuid4()

    # get_group_by_admin → None (user is not admin yet)
    # get_membership → None (user is not a member yet)
    # create_family_group → new group
    # add_member → membership
    # get_group_by_id → full group for response DTO
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,  # get_group_by_admin
        None,  # get_membership
    ]

    created_group = _mock_group(group_id=group_id, admin_id=user_id)
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()

    def refresh_side_effect(obj):
        if isinstance(obj, FamilyGroup) or hasattr(obj, "family_group_id"):
            obj.family_group_id = group_id
            obj.name = "Familia Test"
            obj.admin_id = user_id

    mock_db.refresh = MagicMock(side_effect=refresh_side_effect)

    # get_group_by_id (with joinedload) for _load_group_dto
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
        created_group
    )

    response = client.post(
        "/v1/family-group",
        json={"name": "Familia Test"},
    )

    assert response.status_code == 201


def test_create_family_group_empty_name(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    response = client.post("/v1/family-group", json={"name": ""})

    # Pydantic min_length=1 rejects empty name before the service is even called
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/family-group — Get my group
# ---------------------------------------------------------------------------


def test_get_my_group_not_found(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    # Not admin, not member
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

    response = client.get("/v1/family-group")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/family-group/invitation — Send invitation
# ---------------------------------------------------------------------------


def test_send_invitation_not_admin_returns_403(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    # Caller is not admin → get_group_by_admin returns None
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post(
        "/v1/family-group/invitation",
        json={"email": "someone@test.cl"},
    )
    print(response.json())
    assert response.status_code == 403


def test_send_invitation_user_not_found_returns_404(client: TestClient, mock_db: MagicMock):
    admin_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=admin_id)

    group = _mock_group(admin_id=admin_id)

    # get_group_by_admin → group; get_user_by_email → None
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        group,  # get_group_by_admin
        None,   # get_user_by_email
    ]

    response = client.post(
        "/v1/family-group/invitation",
        json={"email": "ghost@test.cl"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /v1/family-group/invitation/accept — Accept invitation
# ---------------------------------------------------------------------------


def test_accept_invitation_not_found_returns_404(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    # get_join_request_by_id → None
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.patch(
        "/v1/family-group/invitation/accept",
        json={"invitation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_accept_invitation_wrong_user_returns_403(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    # Request belongs to a different user
    req = MagicMock(spec=GroupJoinRequest)
    req.group_join_request_id = uuid.uuid4()
    req.requester_user_id = uuid.uuid4()  # different user
    req.status = "pending"
    req.family_group_id = uuid.uuid4()

    mock_db.query.return_value.filter.return_value.first.return_value = req

    response = client.patch(
        "/v1/family-group/invitation/accept",
        json={"invitation_id": str(req.group_join_request_id)},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /v1/family-group/invitation/decline — Decline invitation
# ---------------------------------------------------------------------------


def test_decline_invitation_not_found_returns_404(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=user_id)

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.patch(
        "/v1/family-group/invitation/decline",
        json={"invitation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /v1/family-group/member — Remove member
# ---------------------------------------------------------------------------


def test_remove_member_not_admin_returns_403(client: TestClient, mock_db: MagicMock):
    admin_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id=admin_id)

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.delete(
        f"/v1/family-group/member?user_id={uuid.uuid4()}"
    )
    assert response.status_code == 403
