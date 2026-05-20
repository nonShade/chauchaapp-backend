"""
Groups repository — data access layer.
"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.modules.groups.entities import FamilyGroup, GroupJoinRequest, GroupMember
from app.modules.users.entities import User


class GroupsRepository:
    """Data access for family groups, members and join requests."""

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # FamilyGroup
    # ------------------------------------------------------------------

    def create_family_group(self, group: FamilyGroup) -> FamilyGroup:
        """Persist a new family group and return it with generated PK."""
        self._session.add(group)
        self._session.commit()
        self._session.refresh(group)
        return group

    def get_group_by_id(self, group_id: UUID) -> FamilyGroup | None:
        """Return a family group with its admin and member relationships loaded."""
        return (
            self._session.query(FamilyGroup)
            .options(
                joinedload(FamilyGroup.admin),
                joinedload(FamilyGroup.members).joinedload(GroupMember.user),
            )
            .filter(FamilyGroup.family_group_id == group_id)
            .first()
        )

    def get_group_by_admin(self, admin_id: UUID) -> FamilyGroup | None:
        """Return the family group where the given user is the administrator."""
        return (
            self._session.query(FamilyGroup)
            .filter(FamilyGroup.admin_id == admin_id)
            .first()
        )

    # ------------------------------------------------------------------
    # GroupMember
    # ------------------------------------------------------------------

    def get_membership(self, user_id: UUID) -> GroupMember | None:
        """Return the membership record for the user (if any)."""
        return (
            self._session.query(GroupMember)
            .filter(GroupMember.user_id == user_id)
            .first()
        )

    def get_membership_in_group(
        self, user_id: UUID, group_id: UUID
    ) -> GroupMember | None:
        """Return the membership record for the user in a specific group."""
        return (
            self._session.query(GroupMember)
            .filter(
                GroupMember.user_id == user_id,
                GroupMember.family_group_id == group_id,
            )
            .first()
        )

    def add_member(self, member: GroupMember) -> GroupMember:
        """Add a user to a family group."""
        self._session.add(member)
        self._session.commit()
        self._session.refresh(member)
        return member

    def remove_member(self, member: GroupMember) -> None:
        """Remove a user from a family group."""
        self._session.delete(member)
        self._session.commit()

    # ------------------------------------------------------------------
    # GroupJoinRequest
    # ------------------------------------------------------------------

    def create_join_request(self, request: GroupJoinRequest) -> GroupJoinRequest:
        """Persist a new join request."""
        self._session.add(request)
        self._session.commit()
        self._session.refresh(request)
        return request

    def get_join_request_by_id(
        self, request_id: UUID
    ) -> GroupJoinRequest | None:
        """Return a join request by its primary key."""
        return (
            self._session.query(GroupJoinRequest)
            .filter(GroupJoinRequest.group_join_request_id == request_id)
            .first()
        )

    def get_pending_request(
        self, user_id: UUID, group_id: UUID
    ) -> GroupJoinRequest | None:
        """Return a pending join request from a user to a specific group."""
        return (
            self._session.query(GroupJoinRequest)
            .filter(
                GroupJoinRequest.requester_user_id == user_id,
                GroupJoinRequest.family_group_id == group_id,
                GroupJoinRequest.status == "pending",
            )
            .first()
        )

    def update_join_request(self, request: GroupJoinRequest) -> GroupJoinRequest:
        """Persist status changes to an existing join request."""
        self._session.commit()
        self._session.refresh(request)
        return request

    # ------------------------------------------------------------------
    # User look-ups (used by service for validation)
    # ------------------------------------------------------------------

    def get_user_by_email(self, email: str) -> User | None:
        """Find a registered user by e-mail address."""
        return (
            self._session.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_user_by_id(self, user_id: UUID) -> User | None:
        """Find a registered user by their primary key."""
        return (
            self._session.query(User)
            .filter(User.user_id == user_id)
            .first()
        )
