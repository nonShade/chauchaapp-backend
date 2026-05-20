"""
Groups module DTOs.

Handles data transfer formatting for the Family Group endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateFamilyGroupDTO(BaseModel):
    """Payload for creating a new family group."""

    name: str = Field(..., min_length=1, max_length=100)


class InviteMemberDTO(BaseModel):
    """Payload for inviting a user to a family group by e-mail."""

    email: EmailStr


class RespondInvitationDTO(BaseModel):
    """Payload for accepting or declining a join-request invitation."""

    invitation_id: UUID


class RemoveMemberDTO(BaseModel):
    """Payload for removing a member from a group (admin only)."""

    user_id: UUID


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class GroupMemberResponseDTO(BaseModel):
    """Minimal user info returned inside a group listing."""

    user_id: UUID
    first_name: str
    last_name: str
    email: str

    model_config = {"from_attributes": True}


class FamilyGroupResponseDTO(BaseModel):
    """Full family group response including admin and member list."""

    family_group_id: UUID
    name: str
    admin: GroupMemberResponseDTO
    members: list[GroupMemberResponseDTO]

    model_config = {"from_attributes": True}


class InvitationSentResponseDTO(BaseModel):
    """Response returned after successfully sending an invitation."""

    message: str
    invitation_id: UUID


class InvitationResponseDTO(BaseModel):
    """Response after accepting or declining an invitation."""

    message: str
    family_group_id: UUID


class RemoveMemberResponseDTO(BaseModel):
    """Response after removing a member."""

    message: str
    family_group_id: UUID
