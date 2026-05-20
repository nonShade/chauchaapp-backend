"""
Groups controller — HTTP endpoint layer.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.modules.groups.dto import (
    CreateFamilyGroupDTO,
    FamilyGroupResponseDTO,
    InviteMemberDTO,
    InvitationResponseDTO,
    InvitationSentResponseDTO,
    RemoveMemberResponseDTO,
    RespondInvitationDTO,
)
from app.modules.groups.repository import GroupsRepository
from app.modules.groups.service import GroupsService
from app.modules.notifications.repository import NotificationsRepository
from app.modules.users.entities import User
from app.shared.database import get_db
from app.shared.security.auth_middleware import get_current_user

router = APIRouter(prefix="/v1/family-group", tags=["Family Group"])


def _get_groups_service(db: Session = Depends(get_db)) -> GroupsService:
    """Dependency builder for GroupsService."""
    return GroupsService(
        groups_repo=GroupsRepository(db),
        notifications_repo=NotificationsRepository(db),
    )


@router.post(
    "",
    response_model=FamilyGroupResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear grupo familiar",
    description="Crea un nuevo grupo familiar. El usuario autenticado se convierte en administrador.",
)
def create_family_group(
    data: CreateFamilyGroupDTO,
    user: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Create a new family group for the authenticated user."""
    return service.create_family_group(user.user_id, data.name)


@router.get(
    "",
    response_model=FamilyGroupResponseDTO,
    summary="Ver mi grupo familiar",
    description="Retorna el grupo familiar al que pertenece el usuario autenticado.",
)
def get_my_group(
    user: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Get the family group for the current user."""
    return service.get_my_group(user.user_id)


@router.post(
    "/invitation",
    response_model=InvitationSentResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar invitación",
    description="El administrador envía una invitación a otro usuario por correo electrónico.",
)
def send_invitation(
    data: InviteMemberDTO,
    user: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Admin sends a group invitation to a user by email."""
    return service.send_invitation(user.user_id, data.email)


@router.patch(
    "/invitation/accept",
    response_model=InvitationResponseDTO,
    summary="Aceptar invitación",
    description="El usuario invitado acepta la solicitud para unirse al grupo familiar.",
)
def accept_invitation(
    data: RespondInvitationDTO,
    user: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Accept a pending group invitation."""
    return service.accept_invitation(user.user_id, data.invitation_id)


@router.patch(
    "/invitation/decline",
    response_model=InvitationResponseDTO,
    summary="Rechazar invitación",
    description="El usuario invitado rechaza la solicitud para unirse al grupo familiar.",
)
def decline_invitation(
    data: RespondInvitationDTO,
    user: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Decline a pending group invitation."""
    return service.decline_invitation(user.user_id, data.invitation_id)


@router.delete(
    "/member",
    response_model=RemoveMemberResponseDTO,
    summary="Eliminar miembro",
    description="El administrador del grupo elimina a un miembro.",
)
def remove_member(
    user_id: UUID = Query(..., description="ID del usuario a eliminar"),
    admin: User = Depends(get_current_user),
    service: GroupsService = Depends(_get_groups_service),
):
    """Remove a member from the family group (admin only)."""
    return service.remove_member(admin.user_id, user_id)
