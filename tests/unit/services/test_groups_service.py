"""
Unit tests for GroupsService.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.modules.groups.entities import FamilyGroup, GroupJoinRequest, GroupMember
from app.modules.groups.repository import GroupsRepository
from app.modules.groups.service import GroupsService
from app.modules.notifications.entities import Notification, NotificationStatus, NotificationType
from app.modules.notifications.repository import NotificationsRepository
from app.modules.users.entities import User
from app.shared.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_groups_repo():
    return MagicMock(spec=GroupsRepository)


@pytest.fixture
def mock_notif_repo():
    return MagicMock(spec=NotificationsRepository)


@pytest.fixture
def service(mock_groups_repo, mock_notif_repo):
    return GroupsService(mock_groups_repo, mock_notif_repo)


def _make_user(user_id=None, email="user@test.cl", first_name="Juan", last_name="Pérez"):
    user = MagicMock(spec=User)
    user.user_id = user_id or uuid.uuid4()
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    return user


def _make_group(group_id=None, admin_id=None, name="Mi Grupo"):
    group = MagicMock(spec=FamilyGroup)
    group.family_group_id = group_id or uuid.uuid4()
    group.admin_id = admin_id or uuid.uuid4()
    group.name = name
    admin = _make_user(user_id=group.admin_id)
    group.admin = admin
    group.members = []
    return group


def _make_join_request(request_id=None, group_id=None, requester_id=None, status="pending"):
    req = MagicMock(spec=GroupJoinRequest)
    req.group_join_request_id = request_id or uuid.uuid4()
    req.family_group_id = group_id or uuid.uuid4()
    req.requester_user_id = requester_id or uuid.uuid4()
    req.status = status
    return req


# ---------------------------------------------------------------------------
# create_family_group
# ---------------------------------------------------------------------------


class TestCreateFamilyGroup:
    def test_creates_group_successfully(self, service, mock_groups_repo, mock_notif_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = None
        mock_groups_repo.get_membership.return_value = None

        created_group = _make_group(admin_id=admin_id, name="Familia Test")
        mock_groups_repo.create_family_group.return_value = created_group
        mock_groups_repo.add_member.return_value = MagicMock(spec=GroupMember)
        mock_groups_repo.get_group_by_id.return_value = created_group

        result = service.create_family_group(admin_id, "Familia Test")

        mock_groups_repo.create_family_group.assert_called_once()
        mock_groups_repo.add_member.assert_called_once()
        assert result.name == "Familia Test"

    def test_raises_if_already_admin(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)

        with pytest.raises(ConflictException):
            service.create_family_group(admin_id, "Nuevo Grupo")

    def test_raises_if_already_member(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = None
        mock_groups_repo.get_membership.return_value = MagicMock(spec=GroupMember)

        with pytest.raises(ConflictException):
            service.create_family_group(admin_id, "Nuevo Grupo")

    def test_raises_if_name_is_empty(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = None
        mock_groups_repo.get_membership.return_value = None

        with pytest.raises(ValidationException):
            service.create_family_group(admin_id, "   ")


# ---------------------------------------------------------------------------
# get_my_group
# ---------------------------------------------------------------------------


class TestGetMyGroup:
    def test_returns_group_for_admin(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        group = _make_group(admin_id=admin_id)
        mock_groups_repo.get_group_by_admin.return_value = group
        mock_groups_repo.get_group_by_id.return_value = group

        result = service.get_my_group(admin_id)

        assert result.family_group_id == group.family_group_id

    def test_returns_group_for_member(self, service, mock_groups_repo):
        user_id = uuid.uuid4()
        group = _make_group()
        membership = MagicMock(spec=GroupMember)
        membership.family_group_id = group.family_group_id

        mock_groups_repo.get_group_by_admin.return_value = None
        mock_groups_repo.get_membership.return_value = membership
        mock_groups_repo.get_group_by_id.return_value = group

        result = service.get_my_group(user_id)

        assert result.family_group_id == group.family_group_id

    def test_raises_if_user_has_no_group(self, service, mock_groups_repo):
        user_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = None
        mock_groups_repo.get_membership.return_value = None

        with pytest.raises(NotFoundException):
            service.get_my_group(user_id)


# ---------------------------------------------------------------------------
# send_invitation
# ---------------------------------------------------------------------------


class TestSendInvitation:
    def test_sends_invitation_successfully(self, service, mock_groups_repo, mock_notif_repo):
        admin_id = uuid.uuid4()
        target = _make_user(email="target@test.cl")
        group = _make_group(admin_id=admin_id)
        group.admin = _make_user(user_id=admin_id)

        mock_groups_repo.get_group_by_admin.return_value = group
        mock_groups_repo.get_user_by_email.return_value = target
        mock_groups_repo.get_membership.return_value = None
        mock_groups_repo.get_pending_request.return_value = None
        mock_groups_repo.get_user_by_id.return_value = group.admin

        created_req = _make_join_request(
            group_id=group.family_group_id,
            requester_id=target.user_id,
        )
        mock_groups_repo.create_join_request.return_value = created_req

        notif_type = MagicMock(spec=NotificationType)
        notif_type.notification_type_id = uuid.uuid4()
        notif_status = MagicMock(spec=NotificationStatus)
        notif_status.notification_status_id = uuid.uuid4()
        mock_notif_repo.get_notification_type_by_name.return_value = notif_type
        mock_notif_repo.get_notification_status_by_name.return_value = notif_status
        mock_notif_repo.create_notification.return_value = MagicMock(spec=Notification)

        result = service.send_invitation(admin_id, "target@test.cl")

        assert result.invitation_id == created_req.group_join_request_id
        mock_notif_repo.create_notification.assert_called_once()

    def test_raises_if_caller_is_not_admin(self, service, mock_groups_repo):
        mock_groups_repo.get_group_by_admin.return_value = None

        with pytest.raises(ForbiddenException):
            service.send_invitation(uuid.uuid4(), "someone@test.cl")

    def test_raises_if_target_not_found(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)
        mock_groups_repo.get_user_by_email.return_value = None

        with pytest.raises(NotFoundException):
            service.send_invitation(admin_id, "ghost@test.cl")

    def test_raises_if_target_already_in_group(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        target = _make_user()
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)
        mock_groups_repo.get_user_by_email.return_value = target
        mock_groups_repo.get_membership.return_value = MagicMock(spec=GroupMember)

        with pytest.raises(ConflictException):
            service.send_invitation(admin_id, target.email)

    def test_raises_if_duplicate_pending_invitation(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        target = _make_user()
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)
        mock_groups_repo.get_user_by_email.return_value = target
        mock_groups_repo.get_membership.return_value = None
        mock_groups_repo.get_pending_request.return_value = MagicMock(spec=GroupJoinRequest)

        with pytest.raises(ConflictException):
            service.send_invitation(admin_id, target.email)

    def test_raises_if_inviting_self(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        admin_user = _make_user(user_id=admin_id)
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)
        mock_groups_repo.get_user_by_email.return_value = admin_user

        with pytest.raises(ValidationException):
            service.send_invitation(admin_id, admin_user.email)


# ---------------------------------------------------------------------------
# accept_invitation
# ---------------------------------------------------------------------------


class TestAcceptInvitation:
    def test_accepts_successfully(self, service, mock_groups_repo, mock_notif_repo):
        user_id = uuid.uuid4()
        req = _make_join_request(requester_id=user_id)

        mock_groups_repo.get_join_request_by_id.return_value = req
        mock_groups_repo.get_membership.return_value = None
        mock_groups_repo.add_member.return_value = MagicMock(spec=GroupMember)
        mock_groups_repo.update_join_request.return_value = req
        mock_notif_repo.get_pending_invitation_notification.return_value = None

        result = service.accept_invitation(user_id, req.group_join_request_id)

        assert result.family_group_id == req.family_group_id
        mock_groups_repo.add_member.assert_called_once()

    def test_raises_if_request_not_found(self, service, mock_groups_repo):
        mock_groups_repo.get_join_request_by_id.return_value = None

        with pytest.raises(NotFoundException):
            service.accept_invitation(uuid.uuid4(), uuid.uuid4())

    def test_raises_if_request_not_pending(self, service, mock_groups_repo):
        user_id = uuid.uuid4()
        req = _make_join_request(requester_id=user_id, status="accepted")
        mock_groups_repo.get_join_request_by_id.return_value = req

        with pytest.raises(NotFoundException):
            service.accept_invitation(user_id, req.group_join_request_id)

    def test_raises_if_user_not_requester(self, service, mock_groups_repo):
        req = _make_join_request(requester_id=uuid.uuid4())
        mock_groups_repo.get_join_request_by_id.return_value = req

        with pytest.raises(ForbiddenException):
            service.accept_invitation(uuid.uuid4(), req.group_join_request_id)

    def test_raises_if_already_member(self, service, mock_groups_repo):
        user_id = uuid.uuid4()
        req = _make_join_request(requester_id=user_id)
        mock_groups_repo.get_join_request_by_id.return_value = req
        mock_groups_repo.get_membership.return_value = MagicMock(spec=GroupMember)

        with pytest.raises(ConflictException):
            service.accept_invitation(user_id, req.group_join_request_id)


# ---------------------------------------------------------------------------
# decline_invitation
# ---------------------------------------------------------------------------


class TestDeclineInvitation:
    def test_declines_successfully(self, service, mock_groups_repo, mock_notif_repo):
        user_id = uuid.uuid4()
        req = _make_join_request(requester_id=user_id)
        mock_groups_repo.get_join_request_by_id.return_value = req
        mock_groups_repo.update_join_request.return_value = req
        mock_notif_repo.get_pending_invitation_notification.return_value = None

        result = service.decline_invitation(user_id, req.group_join_request_id)

        assert result.family_group_id == req.family_group_id
        assert req.status == "declined"

    def test_raises_if_request_not_found(self, service, mock_groups_repo):
        mock_groups_repo.get_join_request_by_id.return_value = None

        with pytest.raises(NotFoundException):
            service.decline_invitation(uuid.uuid4(), uuid.uuid4())

    def test_raises_if_user_not_requester(self, service, mock_groups_repo):
        req = _make_join_request(requester_id=uuid.uuid4())
        mock_groups_repo.get_join_request_by_id.return_value = req

        with pytest.raises(ForbiddenException):
            service.decline_invitation(uuid.uuid4(), req.group_join_request_id)


# ---------------------------------------------------------------------------
# remove_member
# ---------------------------------------------------------------------------


class TestRemoveMember:
    def test_removes_member_successfully(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()
        group = _make_group(admin_id=admin_id)
        target_user = _make_user(user_id=target_id)
        membership = MagicMock(spec=GroupMember)

        mock_groups_repo.get_group_by_admin.return_value = group
        mock_groups_repo.get_user_by_id.return_value = target_user
        mock_groups_repo.get_membership_in_group.return_value = membership

        result = service.remove_member(admin_id, target_id)

        mock_groups_repo.remove_member.assert_called_once_with(membership)
        assert result.family_group_id == group.family_group_id

    def test_raises_if_caller_not_admin(self, service, mock_groups_repo):
        mock_groups_repo.get_group_by_admin.return_value = None

        with pytest.raises(ForbiddenException):
            service.remove_member(uuid.uuid4(), uuid.uuid4())

    def test_raises_if_removing_self(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        mock_groups_repo.get_group_by_admin.return_value = _make_group(admin_id=admin_id)

        with pytest.raises(ValidationException):
            service.remove_member(admin_id, admin_id)

    def test_raises_if_target_not_in_group(self, service, mock_groups_repo):
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()
        group = _make_group(admin_id=admin_id)
        target_user = _make_user(user_id=target_id)

        mock_groups_repo.get_group_by_admin.return_value = group
        mock_groups_repo.get_user_by_id.return_value = target_user
        mock_groups_repo.get_membership_in_group.return_value = None

        with pytest.raises(ConflictException):
            service.remove_member(admin_id, target_id)
