"""
Groups service — business logic layer.
"""

from datetime import datetime
from uuid import UUID

from app.modules.groups.dto import (
    FamilyGroupResponseDTO,
    GroupMemberResponseDTO,
    InvitationResponseDTO,
    InvitationSentResponseDTO,
    RemoveMemberResponseDTO,
)
from app.modules.groups.entities import FamilyGroup, GroupJoinRequest, GroupMember
from app.modules.groups.repository import GroupsRepository
from app.modules.notifications.entities import Notification
from app.modules.notifications.repository import NotificationsRepository
from app.shared.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)


class GroupsService:
    """Business logic for family groups and group invitations."""

    def __init__(
        self,
        groups_repo: GroupsRepository,
        notifications_repo: NotificationsRepository,
    ):
        self._groups = groups_repo
        self._notifications = notifications_repo

    # ------------------------------------------------------------------
    # Create group
    # ------------------------------------------------------------------

    def create_family_group(self, admin_id: UUID, name: str) -> FamilyGroupResponseDTO:
        """Create a new family group with the calling user as administrator.

        Rules:
        - name must not be blank (enforced by DTO, double-checked here).
        - The user must not already be the admin of a group.
        - The user must not already be a member of a group.
        """
        if not name or not name.strip():
            raise ValidationException("El nombre del grupo no puede estar vacío")

        if self._groups.get_group_by_admin(admin_id):
            raise ConflictException("Ya eres administrador de un grupo familiar")

        if self._groups.get_membership(admin_id):
            raise ConflictException("Ya perteneces a un grupo familiar")

        group = FamilyGroup(name=name.strip(), admin_id=admin_id)
        group = self._groups.create_family_group(group)

        # The admin is also a member
        member = GroupMember(user_id=admin_id, family_group_id=group.family_group_id)
        self._groups.add_member(member)

        return self._load_group_dto(group.family_group_id)

    # ------------------------------------------------------------------
    # Get group
    # ------------------------------------------------------------------

    def get_my_group(self, user_id: UUID) -> FamilyGroupResponseDTO:
        """Return the family group the user belongs to (as admin or member).

        Raises NotFoundException if the user has no group.
        """
        # Check if user is admin
        group = self._groups.get_group_by_admin(user_id)
        if not group:
            # Check if user is a member
            membership = self._groups.get_membership(user_id)
            if not membership:
                raise NotFoundException(
                    "No perteneces a ningún grupo familiar"
                )
            group = self._groups.get_group_by_id(membership.family_group_id)
            if not group:
                raise NotFoundException("Grupo familiar no encontrado")

        return self._load_group_dto(group.family_group_id)

    # ------------------------------------------------------------------
    # Send invitation
    # ------------------------------------------------------------------

    def send_invitation(
        self, admin_id: UUID, invited_email: str
    ) -> InvitationSentResponseDTO:
        """Admin sends an invitation to a user by e-mail.

        Generates a GroupJoinRequest and a Notification for the invited user.

        Rules:
        - Caller must be admin of a group.
        - Target user must exist and not already belong to a group.
        - A pending invitation from the same group must not already exist.
        """
        # Verify caller is admin
        group = self._groups.get_group_by_admin(admin_id)
        if not group:
            raise ForbiddenException(
                "Debes ser administrador de un grupo familiar para enviar invitaciones"
            )

        # Verify target user exists
        target_user = self._groups.get_user_by_email(invited_email)
        if not target_user:
            raise NotFoundException(
                f"No existe ningún usuario registrado con el correo {invited_email}"
            )

        if target_user.user_id == admin_id:
            raise ValidationException("No puedes invitarte a ti mismo")

        # Verify target has no group
        if self._groups.get_membership(target_user.user_id):
            raise ConflictException(
                "El usuario ya pertenece a un grupo familiar"
            )

        # Check for duplicate pending invitation
        existing = self._groups.get_pending_request(
            target_user.user_id, group.family_group_id
        )
        if existing:
            raise ConflictException(
                "Ya existe una invitación pendiente para este usuario"
            )

        # Create join request
        join_request = GroupJoinRequest(
            family_group_id=group.family_group_id,
            requester_user_id=target_user.user_id,
            status="pending",
        )
        join_request = self._groups.create_join_request(join_request)

        # Create notification for the invited user
        notif_type = self._notifications.get_notification_type_by_name(
            "group_join_request"
        )
        notif_status = self._notifications.get_notification_status_by_name("pending")

        if notif_type and notif_status:
            admin_user = self._groups.get_user_by_id(admin_id)
            admin_name = (
                f"{admin_user.first_name} {admin_user.last_name}"
                if admin_user
                else "El administrador"
            )
            notification = Notification(
                user_id=target_user.user_id,
                notification_type_id=notif_type.notification_type_id,
                notification_status_id=notif_status.notification_status_id,
                message=(
                    f"{admin_name} te ha invitado a unirte al grupo "
                    f"familiar «{group.name}»"
                ),
                reference_id=join_request.group_join_request_id,
                reference_type="group_join_request",
            )
            self._notifications.create_notification(notification)

        return InvitationSentResponseDTO(
            message="La invitación se ha enviado correctamente",
            invitation_id=join_request.group_join_request_id,
        )

    # ------------------------------------------------------------------
    # Accept invitation
    # ------------------------------------------------------------------

    def accept_invitation(
        self, user_id: UUID, invitation_id: UUID
    ) -> InvitationResponseDTO:
        """User accepts a pending join invitation.

        Adds the user as a group member and marks the notification as read.
        """
        join_request = self._groups.get_join_request_by_id(invitation_id)
        if not join_request or join_request.status != "pending":
            raise NotFoundException(
                "No tienes una invitación pendiente para este grupo"
            )

        if join_request.requester_user_id != user_id:
            raise ForbiddenException(
                "Esta invitación no te pertenece"
            )

        if self._groups.get_membership(user_id):
            raise ConflictException("Ya perteneces a un grupo familiar activo")

        # Accept: add member
        member = GroupMember(
            user_id=user_id,
            family_group_id=join_request.family_group_id,
        )
        self._groups.add_member(member)

        # Update request status
        join_request.status = "accepted"
        join_request.responded_by = user_id
        join_request.responded_at = datetime.utcnow()
        self._groups.update_join_request(join_request)

        # Mark notification as read
        notification = self._notifications.get_pending_invitation_notification(
            user_id, invitation_id
        )
        if notification:
            self._notifications.update_notification_status(notification, "read")

        return InvitationResponseDTO(
            message="Te has unido al grupo familiar correctamente",
            family_group_id=join_request.family_group_id,
        )

    # ------------------------------------------------------------------
    # Decline invitation
    # ------------------------------------------------------------------

    def decline_invitation(
        self, user_id: UUID, invitation_id: UUID
    ) -> InvitationResponseDTO:
        """User declines a pending join invitation."""
        join_request = self._groups.get_join_request_by_id(invitation_id)
        if not join_request or join_request.status != "pending":
            raise NotFoundException(
                "No tienes una invitación pendiente para este grupo"
            )

        if join_request.requester_user_id != user_id:
            raise ForbiddenException("Esta invitación no te pertenece")

        # Update request status
        join_request.status = "declined"
        join_request.responded_by = user_id
        join_request.responded_at = datetime.utcnow()
        self._groups.update_join_request(join_request)

        # Dismiss notification
        notification = self._notifications.get_pending_invitation_notification(
            user_id, invitation_id
        )
        if notification:
            self._notifications.update_notification_status(notification, "dismissed")

        return InvitationResponseDTO(
            message="Has rechazado la solicitud para unirte al grupo familiar",
            family_group_id=join_request.family_group_id,
        )

    # ------------------------------------------------------------------
    # Remove member
    # ------------------------------------------------------------------

    def remove_member(
        self, admin_id: UUID, target_user_id: UUID
    ) -> RemoveMemberResponseDTO:
        """Admin removes a member from their family group.

        The admin themselves cannot be removed via this endpoint.
        """
        group = self._groups.get_group_by_admin(admin_id)
        if not group:
            raise ForbiddenException(
                "Debes ser administrador del grupo para eliminar miembros"
            )

        if target_user_id == admin_id:
            raise ValidationException(
                "El administrador no puede eliminarse a sí mismo del grupo"
            )

        target_user = self._groups.get_user_by_id(target_user_id)
        if not target_user:
            raise NotFoundException("Usuario no encontrado")

        membership = self._groups.get_membership_in_group(
            target_user_id, group.family_group_id
        )
        if not membership:
            raise ConflictException(
                "El usuario no pertenece a este grupo familiar"
            )

        self._groups.remove_member(membership)

        return RemoveMemberResponseDTO(
            message="Se ha eliminado el miembro del grupo familiar correctamente",
            family_group_id=group.family_group_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_group_dto(self, group_id: UUID) -> FamilyGroupResponseDTO:
        """Reload group with all relationships and map to response DTO."""
        group = self._groups.get_group_by_id(group_id)
        if not group:
            raise NotFoundException("Grupo familiar no encontrado")

        admin_dto = GroupMemberResponseDTO(
            user_id=group.admin.user_id,
            first_name=group.admin.first_name,
            last_name=group.admin.last_name,
            email=group.admin.email,
        )

        members_dto = [
            GroupMemberResponseDTO(
                user_id=m.user.user_id,
                first_name=m.user.first_name,
                last_name=m.user.last_name,
                email=m.user.email,
            )
            for m in group.members
            if m.user_id != group.admin_id  # exclude admin from members list
        ]

        return FamilyGroupResponseDTO(
            family_group_id=group.family_group_id,
            name=group.name,
            admin=admin_dto,
            members=members_dto,
        )
